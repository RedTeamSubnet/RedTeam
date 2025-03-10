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

        """
        Add baseline image to compare with miners
        """
        self.baseline_image = self.challenge_info.get("baseline", None)
        self.uid_baseline = -1
        if self.baseline_image:
            self.miner_docker_images.insert(0, self.baseline_image)
            self.uids.insert(0, self.uid_baseline)

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
        self._check_container_alive(
            container, health_port=constants.CHALLENGE_DOCKER_PORT, is_challenger=True
        )
        num_task = self.challenge_info.get(
            "num_tasks", constants.N_CHALLENGES_PER_EPOCH
        )
        challenges = [self._get_challenge_from_container() for _ in range(num_task)]
        logs = []  # Logs for miners
        baseline_logs = []  # Logs for baseline
        for miner_docker_image, uid in zip(self.miner_docker_images, self.uids):
            try:
                is_image_valid = self._validate_image_with_digest(miner_docker_image)
                if not is_image_valid:
                    logs.append(
                        {
                            "miner_input": None,
                            "miner_output": None,
                            "score": 0,
                            "miner_docker_image": miner_docker_image,
                            "uid": uid,
                            "error": f"Invalid image format: {miner_docker_image}. Must include a SHA256 digest. Skip evaluation!",
                        }
                    )
                    continue
                bt.logging.info(
                    f"[Controller] Running miner {uid}: {miner_docker_image}"
                )
                self._clear_container_by_port(constants.MINER_DOCKER_PORT)

                kwargs = {}
                if self.resource_limits.get("cuda_device_ids") is not None:
                    kwargs["device_requests"] = [
                        docker.types.DeviceRequest(
                            device_ids=self.resource_limits["cuda_device_ids"],
                            capabilities=[["gpu"]],
                        )
                    ]

                miner_start_time = time.time() if uid != self.uid_baseline else None
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

                self._check_container_alive(
                    miner_container,
                    health_port=constants.MINER_DOCKER_PORT,
                    is_challenger=False,
                    timeout=self.challenge_info.get("docker_run_timeout", 600),
                    start_time=miner_start_time,
                )

                for i, miner_input in enumerate(challenges):
                    miner_output, error_message = self._submit_challenge_to_miner(
                        miner_input
                    )
                    score = (
                        self._score_challenge(
                            miner_input=miner_input,
                            miner_output=miner_output,
                            task_id=i,
                        )
                        if miner_output is not None
                        else 0.0
                    )
                    if type(score) == int:
                        score = float(score)
                    elif not type(score) == float:
                        score = 0.0
                    log = {
                        "miner_input": miner_input,
                        "miner_output": miner_output,
                        "score": score,
                        "miner_docker_image": miner_docker_image,
                        "uid": uid,
                    }

                    if uid != self.uid_baseline and len(baseline_logs) > i:
                        log["score"] -= baseline_logs[i]["score"]
                        log["baseline_score"] = baseline_logs[i]["score"]

                    if error_message:
                        log["error"] = error_message

                    if uid == self.uid_baseline:
                        baseline_logs.append(log)
                    else:
                        logs.append(log)
            except Exception as e:
                bt.logging.error(f"Error while processing miner {uid}: {e}")
                if uid != self.uid_baseline:
                    logs.append(
                        {
                            "miner_input": None,
                            "miner_output": None,
                            "score": 0,
                            "miner_docker_image": miner_docker_image,
                            "uid": uid,
                            "error": str(e),
                        }
                    )
            self._clear_container_by_port(constants.MINER_DOCKER_PORT)
            self._clean_up_docker_resources()
        self._remove_challenge_container()
        self._clean_up_docker_resources()
        return logs

    def _clear_container_by_port(self, port):
        """
        Stops and removes all running Docker containers by running port.
        This is useful for cleaning up the environment before starting a new challenge.
        """
        containers = self.docker_client.containers.list(all=True)

        for container in containers:
            try:
                container_ports = container.attrs["NetworkSettings"]["Ports"]
                if any([str(port) in p for p in container_ports]):
                    res = container.remove(force=True)
                    bt.logging.info(f"Removed container {container.name}: {res}")
            except Exception as e:
                bt.logging.error(
                    f"Error while processing container {container.name}: {e}"
                )

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

        if "privileged" in self.challenge_info:
            kwargs["privileged"] = self.challenge_info["privileged"]

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
        Catches and handles all possible errors to ensure cleanup completes gracefully.
        """
        try:
            containers = self.docker_client.containers.list(all=True)
        except Exception as e:
            bt.logging.error(f"[Controller] Failed to list containers: {str(e)}")
            return

        for container in containers:
            try:
                if container.name != self.challenge_name:
                    continue

                retries = 0
                while retries < 5:
                    try:
                        # Refresh container state
                        try:
                            container.reload()
                        except docker.errors.NotFound:
                            bt.logging.info(f"[Controller] Container {container.name} no longer exists")
                            return
                        except Exception as e:
                            bt.logging.warning(f"[Controller] Failed to reload container state: {str(e)}")

                        # Check if container is already stopped
                        if container.status != "exited":
                            bt.logging.info(f"[Controller] Attempting to stop container {container.name} (Try {retries+1}/5)...")
                            try:
                                container.stop(timeout=30)
                                try:
                                    container.wait(condition="not-running", timeout=30)
                                except docker.errors.NotFound:
                                    bt.logging.info(f"[Controller] Container {container.name} no longer exists after stop")
                                    return
                                except Exception as e:
                                    bt.logging.warning(f"[Controller] Wait for container stop failed: {str(e)}")
                            except docker.errors.NotFound:
                                bt.logging.info(f"[Controller] Container {container.name} already stopped/removed")
                                return
                            except docker.errors.APIError as e:
                                if "is already in progress" in str(e):
                                    bt.logging.info(f"[Controller] Stop operation already in progress for {container.name}")
                                    time.sleep(10)  # Wait longer for in-progress operations
                                    continue
                                else:
                                    bt.logging.warning(f"[Controller] Failed to stop container: {str(e)}")

                        bt.logging.info(f"[Controller] Attempting to remove container {container.name} (Try {retries+1}/5)...")
                        try:
                            container.remove(force=True, v=True)
                            bt.logging.info(f"[Controller] Container {container.name} removed successfully")
                            return
                        except docker.errors.NotFound:
                            bt.logging.info(f"[Controller] Container {container.name} already removed")
                            return
                        except docker.errors.APIError as e:
                            if "is already in progress" in str(e):
                                bt.logging.info(f"[Controller] Remove operation already in progress for {container.name}")
                                time.sleep(10)  # Wait longer for in-progress operations
                                # Check if container still exists before continuing
                                try:
                                    container.reload()
                                except docker.errors.NotFound:
                                    bt.logging.info(f"[Controller] Container {container.name} was removed successfully")
                                    return
                                continue
                            bt.logging.warning(f"[Controller] Failed to remove container: {str(e)}")

                    except requests.exceptions.ReadTimeout:
                        bt.logging.warning("[Controller] Timeout while communicating with Docker daemon")
                        time.sleep(5)
                    except Exception as e:
                        bt.logging.warning(f"[Controller] Unexpected error in removal loop: {str(e)}")

                    retries += 1
                    if retries < 5:  # Don't wait if this was the last try
                        try:
                            wait_time = min(5 * (2 ** (retries - 1)), 30)  # Reduced max wait time
                            bt.logging.info(f"[Controller] Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                        except Exception as e:
                            bt.logging.warning(f"[Controller] Error during retry wait: {str(e)}")
                            time.sleep(5)

                bt.logging.error(f"[Controller] Failed to remove container {container.name} after 5 attempts")

            except Exception as e:
                bt.logging.error(f"[Controller] Unexpected error handling container: {str(e)}")
                continue

        try:
            self._clear_container_by_port(constants.CHALLENGE_DOCKER_PORT)
        except Exception as e:
            bt.logging.error(f"[Controller] Failed to clear containers by port: {str(e)}")

    def _submit_challenge_to_miner(self, challenge) -> dict:
        """
        Sends the challenge input to a miner by making an HTTP POST request to a local endpoint.
        The request submits the input, and the miner returns the generated output.

        Args:
            challenge: The input to be solved by the miner.

        Returns:
            A dictionary representing the miner's output.
        """

        error_message = ""
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
            return response.json(), error_message
        except requests.exceptions.Timeout:
            error_message = "Timeout occurred while trying to solve challenge."
            bt.logging.error(error_message)
            return None, error_message
        except Exception as ex:
            error_message = f"Submit challenge to miner failed: {str(ex)}"
            bt.logging.error(error_message)
            return None, error_message

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

    def _score_challenge(self, miner_input, miner_output, task_id: int = 0) -> float:
        """
        Submits the miner's input and output for scoring by making an HTTP POST request to the challenge container.
        The challenge container computes a score based on the miner's performance.

        Args:
            miner_input: The input provided to the miner.
            miner_output: The output generated by the miner.
            task_id: The task ID for the challenge. Defaults to 0.

        Returns:
            A float representing the score for the miner's solution.
        """

        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)

        _reset_challenge = False
        if task_id == 0:
            _reset_challenge = self.challenge_info.get("reset_challenge", False)

        _reset_query = ""
        if _reset_challenge:
            _reset_query = "?reset=true"

        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
            }
            bt.logging.debug(f"[Controller] Scoring payload: {str(payload)[:100]}...")
            response = requests.post(
                f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/score{_reset_query}",
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
                # fmt: off
                # Block forwarded traffic to the internet:
                ["iptables", "-I", "FORWARD", "-s", subnet, "!", "-d", subnet, "-j", "DROP"],
                # Prevent NAT to the internet:
                [ "iptables", "-t", "nat", "-I", "POSTROUTING", "-s", subnet, "-j", "RETURN"]
                # fmt: on
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

    def _clean_up_docker_resources(
        self,
        remove_containers: bool = True,
        remove_images: bool = True,
        remove_networks: bool = False,
    ):
        """Clean up docker resources by removing all exited or dead containers, dangling images, and unused networks."""
        try:
            if remove_containers:
                # Delete all containers that have exited or dead
                bt.logging.info("Removing stopped containers...")
                for container in self.docker_client.containers.list(all=True):
                    if container.status in ["exited", "dead"]:
                        print(
                            f"Removing container {container.name} ({container.id})..."
                        )
                        container.remove(force=True)

            if remove_images:
                # Delete all dangling images
                bt.logging.info("Removing dangling images...")
                for image in self.docker_client.images.list(filters={"dangling": True}):
                    bt.logging.info(f"Removing image {image.id}...")
                    self.docker_client.images.remove(
                        image.id, force=True, noprune=False
                    )

            # Delete unused resources (volumes, build cache)
            bt.logging.info("Pruning unused resources (volumes, build cache)...")
            self.docker_client.api.prune_builds()
            self.docker_client.volumes.prune()
            if remove_networks:
                self.docker_client.networks.prune()

            bt.logging.info("Docker resources cleaned up successfully.")
        except Exception as e:
            bt.logging.error(
                f"An error occurred while cleaning up docker resources: {e}"
            )

    def _check_container_alive(
        self,
        container: docker.models.containers.Container,
        health_port,
        is_challenger=True,
        timeout=None,
        start_time=None,
    ):
        """Check when the container is running successfully"""
        if not start_time:
            start_time = time.time()
        while not self._check_alive(port=health_port, is_challenger=is_challenger) and (
            not timeout or time.time() - start_time < timeout
        ):
            container.reload()
            if container.status in ["exited", "dead"]:
                container_logs = container.logs().decode("utf-8", errors="ignore")
                bt.logging.error(
                    f"[Controller] Container {container} failed with status: {container.status}"
                )
                bt.logging.error(f"[Controller] Container logs:\n{container_logs}")
                raise RuntimeError(
                    f"Container failed to start. Status: {container.status}. Container logs: {container_logs}"
                )
            else:
                bt.logging.info(
                    f"[Controller] Waiting for  container to start. {container.status}"
                )
                time.sleep(5)
