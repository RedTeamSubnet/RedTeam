import re
import time
import copy
import subprocess
from typing import List, Dict, Tuple, Union

import docker
import docker.types
import requests
import bittensor as bt

from ..constants import constants


class Controller:
    """
    A class to manage the lifecycle of a challenge, including the initialization
    of Docker containers for the challenge and miners, as well as submitting and scoring tasks.
    """

    def __init__(
        self,
        challenge_name: str,
        miner_docker_images: List[str],
        uids: List[int],
        challenge_info: Dict,
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
        # self._clear_all_container()
        self._build_challenge_image()
        self._remove_challenge_container()
        self._create_network(self.local_network)

        container = self._run_challenge_container()
        bt.logging.info(f"[Controller] Challenge container started: {container.status}")
        while not self._check_alive(
            port=constants.CHALLENGE_DOCKER_PORT, is_challenger=True
        ):
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
            self._clear_container_by_port(constants.MINER_DOCKER_PORT)

            docker_run_start_time = time.time()
            kwargs = {}
            if self.resource_limits.get("cuda_device_ids") is not None:
                kwargs["device_requests"] = [
                    docker.types.DeviceRequest(
                        device_ids=self.resource_limits["cuda_device_ids"],
                        capabilities=[["gpu"]],
                    )
                ]
            miner_container = self.docker_client.containers.run(
                miner_docker_image,
                detach=True,
                cpu_count=self.resource_limits.get("num_cpus", 2),
                mem_limit=self.resource_limits.get("mem_limit", "1g"),
                environment={
                    "CHALLENGE_NAME": self.challenge_name,
                    **self.challenge_info.get("enviroment", {}),
                },
                ports={
                    f"{constants.MINER_DOCKER_PORT}/tcp": constants.MINER_DOCKER_PORT
                },
                network=self.local_network,
                **kwargs,
            )
            while not self._check_alive(
                port=constants.MINER_DOCKER_PORT, is_challenger=False
            ) and time.time() - docker_run_start_time < self.challenge_info.get(
                "docker_run_timeout", 600
            ):
                bt.logging.info(
                    f"[Controller] Waiting for miner container to start. {miner_container.status}"
                )
                time.sleep(1)
            for miner_input in challenges:
                miner_output = self._submit_challenge_to_miner(miner_input)
                score = (
                    self._score_challenge(miner_input, miner_output)
                    if miner_output is not None
                    else 0
                )
                logs.append(
                    {
                        "miner_input": miner_input,
                        "miner_output": miner_output,
                        "score": score,
                        "miner_docker_image": miner_docker_image,
                        "uid": uid,
                    }
                )
            self._clear_container_by_port(constants.MINER_DOCKER_PORT)
        self._remove_challenge_container()
        return logs

    def _clear_container_by_port(self, port):
        """
        Stops and removes all running Docker containers by running port.
        This is useful for cleaning up the environment before starting a new challenge.
        """
        containers = self.docker_client.containers.list(all=True)

        for container in containers:
            try:
                container_ports = container.attrs['NetworkSettings']['Ports']
                if any([str(port) in p for p in container_ports]):
                    res = container.remove(force=True)
                    bt.logging.info(f"Removed container {container.name}: {res}")
            except Exception as e:
                bt.logging.error(f"Error while processing container {container.name}: {e}")
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

        kwargs = {}
        if "same_network" in self.challenge_info:
            kwargs["network"] = self.local_network

        if "hostname" in self.challenge_info:
            kwargs["hostname"] = self.challenge_info["hostname"]

        container = self.docker_client.containers.run(
            self.challenge_name,
            detach=True,
            ports={
                f"{constants.CHALLENGE_DOCKER_PORT}/tcp": constants.CHALLENGE_DOCKER_PORT
            },
            name=self.challenge_name,
            **kwargs,
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

        self._clear_container_by_port(constants.CHALLENGE_DOCKER_PORT)
        
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
            _protocol, _ssl_verify = self._check_protocol(is_challenger=False)
            response = requests.post(
                f"{_protocol}://localhost:{constants.MINER_DOCKER_PORT}/solve",
                timeout=self.challenge_info.get("challenge_solve_timeout", 60),
                verify=_ssl_verify,
                json=miner_input,
            )
            return response.json()
        except Exception as ex:
            bt.logging.error(f"Submit challenge to miner failed: {str(ex)}")
            return None

    def _check_alive(self, port=10001, is_challenger=True) -> bool:
        """
        Checks if the challenge container is still running.
        """

        _protocol, _ssl_verify = self._check_protocol(is_challenger=is_challenger)

        try:
            response = requests.get(
                f"{_protocol}://localhost:{port}/health",
                verify=_ssl_verify,
            )
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            return False
        return False

    def _get_challenge_from_container(self) -> dict:
        """
        Retrieves a challenge input from the running challenge container by making an HTTP POST request.
        The challenge container returns a task that will be sent to the miners.

        Returns:
            A dictionary representing the challenge input.
        """

        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)

        response = requests.get(
            f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/task",
            verify=_ssl_verify,
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

        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)

        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
            }
            bt.logging.debug(f"[Controller] Scoring payload: {str(payload)[:100]}...")
            response = requests.post(
                f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/score",
                verify=_ssl_verify,
                json=payload,
            )
            return response.json()
        except Exception as ex:
            bt.logging.error(f"Score challenge failed: {str(ex)}")
            return 0

    def _create_network(self, network_name):
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
            subnet = network_info["IPAM"]["Config"][0]["Subnet"]
            iptables_commands = [
                # Block forwarded traffic to the internet
                [
                    "iptables",
                    "-I",
                    "FORWARD",
                    "-s",
                    subnet,
                    "!",
                    "-d",
                    subnet,
                    "-j",
                    "DROP",
                ],
                # Prevent NAT to the internet
                [
                    "iptables",
                    "-t",
                    "nat",
                    "-I",
                    "POSTROUTING",
                    "-s",
                    subnet,
                    "-j",
                    "RETURN",
                ],
            ]

            for cmd in iptables_commands:
                try:
                    # Try with sudo
                    subprocess.run(["sudo"] + cmd, check=True)
                except subprocess.CalledProcessError:
                    # If running with sudo fails, try without sudo
                    subprocess.run(cmd, check=True)

        except docker.errors.APIError as e:
            bt.logging.error(f"Failed to create network: {e}")

    def _validate_image_with_digest(self, image):
        """Validate that the provided Docker image includes a SHA256 digest."""
        digest_pattern = r".+@sha256:[a-fA-F0-9]{64}$"  # Regex for SHA256 digest format
        if not re.match(digest_pattern, image):
            bt.logging.error(
                f"Invalid image format: {image}. Must include a SHA256 digest. Skip evaluation!"
            )
            return False
        return True

    def _check_protocol(
        self, is_challenger: bool = True
    ) -> Tuple[str, Union[bool, None]]:
        """Check the protocol scheme and SSL/TLS verification for the challenger or miner.

        Args:
            is_challenger (bool, optional): Flag to check the protocol for the challenger or miner. Defaults to True.

        Returns:
            Tuple[str, Union[bool, None]]: A tuple containing the protocol scheme and SSL/TLS verification.
        """

        _protocol = "http"
        _ssl_verify: Union[bool, None] = None

        if "protocols" in self.challenge_info:
            _protocols = self.challenge_info["protocols"]

            if is_challenger:
                if "challenger" in _protocols:
                    _protocol = _protocols["challenger"]

                if "challenger_ssl_verify" in _protocols:
                    _ssl_verify = _protocols["challenger_ssl_verify"]

            if not is_challenger:
                if "miner" in _protocols:
                    _protocol = _protocols["miner"]

                if "miner_ssl_verify" in _protocols:
                    _ssl_verify = _protocols["miner_ssl_verify"]

        return _protocol, _ssl_verify
