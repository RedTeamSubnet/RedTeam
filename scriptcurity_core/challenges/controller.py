from typing import List
import docker
import requests
import bittensor as bt
from .. import constants
import time

class Controller:
    """
    A class to manage the lifecycle of a challenge, including the initialization
    of Docker containers for the challenge and miners, as well as submitting and scoring tasks.
    """

    def __init__(
        self, challenge_name: str, miner_docker_images: List[str], uids: List[int]
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
        container = self._run_challenge_container()
        bt.logging.info(f"Challenge container started: {container.status}")
        while not self._check_alive(port=constants.CHALLENGE_DOCKER_PORT):
            bt.logging.info("Waiting for challenge container to start.")
            time.sleep(1)
            
        challenges = [
            self._get_challenge_from_container()
            for _ in range(constants.N_CHALLENGES_PER_EPOCH)
        ]
        logs = {}
        miner_scores = {}
        for miner_docker_image, uid in zip(self.miner_docker_images, self.uids):
            self._clear_miner_container_by_image(miner_docker_image)
            miner_container = self.docker_client.containers.run(
                miner_docker_image,
                detach=True,
                environment={"CHALLENGE_NAME": self.challenge_name},
                ports={f"{constants.MINER_DOCKER_PORT}/tcp": constants.MINER_DOCKER_PORT},
            )
            while not self._check_alive(port=constants.MINER_DOCKER_PORT):
                bt.logging.info(f"Waiting for miner container to start. {miner_container.status}")
                time.sleep(1)
            for miner_input in challenges:
                miner_output = self._submit_challenge_to_miner(miner_input)
                score = self._score_challenge(miner_input, miner_output)
                miner_scores.setdefault(uid, []).append(score)
                logs.setdefault(uid, []).append(
                    (miner_input, miner_output, score, miner_docker_image)
                )
        bt.logging.success(miner_scores)
        miner_scores = {
            uid: sum(scores) / len(scores) for uid, scores in miner_scores.items()
        }
        self._remove_challenge_container()
        return miner_scores, logs
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
            path=f"scriptcurity_core/challenges/{self.challenge_name}",
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
            ports={f"{constants.CHALLENGE_DOCKER_PORT}/tcp": constants.CHALLENGE_DOCKER_PORT},
            name=self.challenge_name,
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
        response = requests.post(
            f"http://localhost:{constants.MINER_DOCKER_PORT}/solve",
            json={
                "miner_input": challenge,
            },
        )
        return response.json()

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
        response = requests.get(f"http://localhost:{constants.CHALLENGE_DOCKER_PORT}/task")
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
        payload = {
            "miner_input": miner_input,
            "miner_output": miner_output,
        }
        bt.logging.info(f"Scoring payload: {payload}")
        response = requests.post(
            f"http://localhost:{constants.CHALLENGE_DOCKER_PORT}/score",
            json=payload,
        )
        return response.json()
