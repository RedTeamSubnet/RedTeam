from typing import List, Dict
import docker
import docker.types
import socket, ipaddress
import requests
import bittensor as bt
from ..constants import constants
import time
import subprocess
import copy
import re

class Controller:
    """
    A class to manage the lifecycle of a challenge, including the initialization
    of Docker containers for the challenge and miners, as well as submitting and scoring tasks.
    """

    def __init__(
        self, challenge_name: str, miner_docker_images: List[str], uids: List[int], challenge_info: Dict
    ):
        """
        Initializes the Controller with the name of the challenge and the list of miner Docker images.
        Also sets up the Docker client for interacting with Docker containers.

        Args:
            challenge_name: The name of the challenge to be executed.
            miner_docker_images: A list of Docker images to be used for the miners.
        """
        self.docker_client = docker.from_env()
        self.challenge_name = challenge_name
        self.miner_docker_images = miner_docker_images
        self.uids = uids
        self.challenge_info = challenge_info
        self.resource_limits = challenge_info["resource_limits"]
        self.local_network = "redteam_local"

    def _clear_all_container(self):
        """
        Stops and removes all running Docker containers.
        This is useful for cleaning up the environment before starting a new challenge.
        """
        containers = self.docker_client.containers.list(all=True)
        for container in containers:
            res = container.remove(force=True)
            bt.logging.info(res)

    def start_challenge(self):
        """
        Starts the challenge by building and running the challenge Docker container.
        Then, for each miner image, it runs the miner in a separate container and submits the challenge.
        It collects the challenge inputs, outputs, and the scores for each miner.

        Returns:
            A tuple containing:
            - miner_scores: A dictionary mapping each miner Docker image to their scores.
            - logs: A dictionary of logs for each miner, detailing the input, output, and score.
        """
        self._clear_all_container()
        self._build_challenge_image()
        self._remove_challenge_container()
        self._create_network(self.local_network)

        

        container = self._run_challenge_container()
        bt.logging.info(f"[Controller] Challenge container started: {container.status}")
        while not self._check_alive(port=constants.CHALLENGE_DOCKER_PORT):
            bt.logging.info("[Controller] Waiting for challenge container to start.")
            time.sleep(1)

        challenges = [
            self._get_challenge_from_container()
            for _ in range(constants.N_CHALLENGES_PER_EPOCH)
        ]
        logs = []
        for miner_docker_image, uid in zip(self.miner_docker_images, self.uids):
            is_image_valid = self._validate_image_with_digest(miner_docker_image)
            if not is_image_valid:
                continue
            bt.logging.info(f"[Controller] Running miner {uid}: {miner_docker_image}")
            self._clear_miner_container_by_image(miner_docker_image)

            docker_run_start_time = time.time()
            kwargs = {}
            if self.resource_limits.get("cuda_device_ids") is not None:
                kwargs["device_requests"] = [docker.types.DeviceRequest(device_ids=self.resource_limits["cuda_device_ids"], capabilities=[['gpu']])]
            miner_container = self.docker_client.containers.run(
                miner_docker_image,
                detach=True,
                cpu_count=self.resource_limits.get("num_cpus", 2),
                mem_limit=self.resource_limits.get("mem_limit", "1g"),
                environment={"CHALLENGE_NAME": self.challenge_name, **self.challenge_info.get("enviroment", {})},
                ports={
                    f"{constants.MINER_DOCKER_PORT}/tcp": constants.MINER_DOCKER_PORT
                },
                network=self.local_network,
                **kwargs           
            )
            while not self._check_alive(port=constants.MINER_DOCKER_PORT) and time.time() - docker_run_start_time < self.challenge_info.get("docker_run_timeout", 600):
                bt.logging.info(
                    f"[Controller] Waiting for miner container to start. {miner_container.status}"
                )
                time.sleep(1)
            for miner_input in challenges: 
                miner_output = self._submit_challenge_to_miner(miner_input)
                score = self._score_challenge(miner_input, miner_output) if miner_output is not None else 0
                logs.append(
                    {
                        "miner_input": miner_input,
                        "miner_output": miner_output,
                        "score": score,
                        "miner_docker_image": miner_docker_image,
                        "uid": uid,
                    }
                )
        self._remove_challenge_container()
        return logs

    def _clear_miner_container_by_image(self, miner_docker_image):
        """
        Stops and removes all running Docker containers for the miner Docker image.
        This is useful for cleaning up the environment before starting a new challenge.

        Args:
            miner_docker_image: The Docker image for the miner to be removed.
        """
        containers = self.docker_client.containers.list(all=True)

        for container in containers:
            tags = container.image.tags
            tags = [t.split(":")[0] for t in tags]
            if miner_docker_image in tags:
                res = container.remove(force=True)
                bt.logging.info(res)

    def _build_challenge_image(self):
        """
        Builds the Docker image for the challenge using the provided challenge name.
        This step is necessary to create the environment in which the challenge will run.
        """
        res = self.docker_client.images.build(
            path=f"redteam_core/challenge_pool/{self.challenge_name}",
            tag=self.challenge_name,
            rm=True,
        )
        bt.logging.info(res)

    def _remove_challenge_image(self):
        """
        Removes the Docker image for the challenge, identified by the challenge name.
        This is useful for cleanup after the challenge has been completed.
        """
        self.docker_client.images.remove(self.challenge_name, force=True)

    def _run_challenge_container(self):
        """
        Runs the Docker container for the challenge using the built image.
        The container runs in detached mode and listens on the port defined by constants.
        """
        container = self.docker_client.containers.run(
            self.challenge_name,
            detach=True,
            ports={
                f"{constants.CHALLENGE_DOCKER_PORT}/tcp": constants.CHALLENGE_DOCKER_PORT
            },
            name=self.challenge_name,
            network="bridge"
        )
        bt.logging.info(container)
        return container

    def _remove_challenge_container(self):
        """
        Stops and removes the Docker container running the challenge.
        This helps in cleaning up the environment after the challenge is done.
        """
        containers = self.docker_client.containers.list(all=True)
        for container in containers:
            if container.name == self.challenge_name:
                res = container.remove(force=True)
                bt.logging.info(res)

    def _submit_challenge_to_miner(self, challenge) -> dict:
        """
        Sends the challenge input to a miner by making an HTTP POST request to a local endpoint.
        The request submits the input, and the miner returns the generated output.

        Args:
            challenge: The input to be solved by the miner.

        Returns:
            A dictionary representing the miner's output.
        """

        miner_input = copy.deepcopy(challenge)
        exclude_miner_input_key = self.challenge_info.get("exclude_miner_input_key", [])
        for key in exclude_miner_input_key:
            miner_input[key] = None
        try:
            response = requests.post(
                f"http://localhost:{constants.MINER_DOCKER_PORT}/solve",
                timeout=self.challenge_info.get("challenge_solve_timeout", 60),
                json=miner_input,
            )
            return response.json()
        except Exception as ex:
            bt.logging.error(f"Submit challenge to miner failed: {str(ex)}")
            return None

    def _check_alive(self, port=10001) -> bool:
        """
        Checks if the challenge container is still running.
        """
        try:
            response = requests.get(f"http://localhost:{port}/health")
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            return False
        return False

    def _get_challenge_from_container(self, is_check_alive=False) -> dict:
        """
        Retrieves a challenge input from the running challenge container by making an HTTP POST request.
        The challenge container returns a task that will be sent to the miners.

        Returns:
            A dictionary representing the challenge input.
        """
        response = requests.get(
            f"http://localhost:{constants.CHALLENGE_DOCKER_PORT}/task"
        )
        return response.json()

    def _score_challenge(self, miner_input, miner_output) -> float:
        """
        Submits the miner's input and output for scoring by making an HTTP POST request to the challenge container.
        The challenge container computes a score based on the miner's performance.

        Args:
            miner_input: The input provided to the miner.
            miner_output: The output generated by the miner.

        Returns:
            A float representing the score for the miner's solution.
        """
        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
            }
            bt.logging.debug(f"[Controller] Scoring payload: {str(payload)[:100]}...")
            response = requests.post(
                f"http://localhost:{constants.CHALLENGE_DOCKER_PORT}/score",
                json=payload,
            )
            return response.json()
        except Exception as ex:
            bt.logging.error(f"Score challenge failed: {str(ex)}")
            return 0
    def _create_network(self, network_name):

        def is_valid_ip(ip_str):
            try:
                """
                Check if the provided IP or subnet is valid.
                """
                ipaddress.ip_network(ip_str, strict=False)
                return True
            except ValueError:
                return False

        def resolve_domain(domain):
            try:
                """
                Resolve the domain name to a list of IP addresses.
                """
                ips = socket.gethostbyname_ex(domain)[2]
                bt.logging.info(f"Resolved {domain} to IPs: {ips}")
                return ips
            except socket.gaierror as e:
                bt.logging.error(f"Could not resolve domain {domain}: {e}")
                return []
        
        def execute_iptables(cmd):
            try:
                # Try with sudo
                subprocess.run(["sudo"] + cmd, check=True)
                bt.logging.info(f"Successfully executed: {' '.join(cmd)}")
            except subprocess.CalledProcessError:
                try:
                    # If running with sudo fails, try without sudo
                    subprocess.run(cmd, check=True)
                    bt.logging.info(f"Successfully executed: {' '.join(cmd)}")
                except subprocess.CalledProcessError as e:
                    bt.logging.error(f"Failed to execute: {' '.join(cmd)}")

        try:
            networks = self.docker_client.networks.list(names=[network_name])
            if not networks:
                network = self.docker_client.networks.create(
                    name=self.local_network,
                    driver="bridge",
                )
                bt.logging.info(f"Network '{network_name}' created successfully.")
            else:
                bt.logging.info(f"Network '{network_name}' already exists.")
                network = self.docker_client.networks.get(network_name)


            network_info = self.docker_client.api.inspect_network(network.id)
            subnet = network_info['IPAM']['Config'][0]['Subnet']
            interface_name = f"br-{network.id[:12]}"  # Docker bridge interface name

            # Check existing rules and remove them if they exist
            def get_existing_rules(chain):
                try:
                    output = subprocess.check_output(["sudo", "iptables", "-S", chain]).decode()
                    return [line.strip() for line in output.split('\n') if interface_name in line]
                except subprocess.CalledProcessError:
                    return []

            # Remove existing rules that match our interface
            for chain in ["FORWARD", "POSTROUTING"]:
                # table = "filter" if chain == "FORWARD" else "nat"
                rules = get_existing_rules(chain)
                
                for rule in rules:
                    try:
                        # Convert iptables-save format to delete command
                        # Remove the first "-A" and add "-D" instead
                        parts = rule.split()
                        if parts[0] == "-A":
                            parts[0] = "-D"
                            cmd = ["iptables"] + parts
                            execute_iptables(cmd)
                            bt.logging.info(f"Removed existing rule: {' '.join(cmd)}")
                    except subprocess.CalledProcessError as e:
                        bt.logging.warning(f"Failed to remove rule: {e}")

            iptables_commands = []

            # Add ACCEPT rules for allowed IPs
            allowed_destinations = self.challenge_info.get("allowed_destinations", [])
            if allowed_destinations:
                resolved_ips = []
                for dest in allowed_destinations:
                    if is_valid_ip(dest):
                        resolved_ips.append(dest)
                    else:
                        domain_ips = resolve_domain(dest)
                        resolved_ips.extend(domain_ips)
                resolved_ips = list(set(resolved_ips))
                bt.logging.info(f"All resolved IPs: {resolved_ips}")

                # Allow established connections
                iptables_commands.append(
                    ["iptables", "-A", "FORWARD", "-i", interface_name, "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"]
                )
                
                # Allow access to specified destinations
                for ip in resolved_ips:
                    iptables_commands.append(
                        ["iptables", "-A", "FORWARD", "-i", interface_name, "-d", ip, "-j", "ACCEPT"]
                    )
                
                # Block all other outgoing internet traffic from this network
                iptables_commands.append(
                    ["iptables", "-A", "FORWARD", "-i", interface_name, "!", "-d", subnet, "-j", "DROP"]
                )
                
                # Allow NAT only for allowed destinations
                for ip in resolved_ips:
                    iptables_commands.append(
                        ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", subnet, "-d", ip, "-j", "MASQUERADE"]
                    )

            for cmd in iptables_commands:
                execute_iptables(cmd)

        except docker.errors.APIError as e:
            bt.logging.error(f"Failed to create network: {e}")
             
    def _validate_image_with_digest(self, image):
        """Validate that the provided Docker image includes a SHA256 digest."""
        digest_pattern = r".+@sha256:[a-fA-F0-9]{64}$"  # Regex for SHA256 digest format
        if not re.match(digest_pattern, image):
            bt.logging.error(f"Invalid image format: {image}. Must include a SHA256 digest. Skip evaluation!")
            return False
        return True
 