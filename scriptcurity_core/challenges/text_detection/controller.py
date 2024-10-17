from typing import List
import docker
import httpx
from ... import constants


class Controller:
    """
    A class to manage the lifecycle of a challenge, including the initialization
    of Docker containers for the challenge and miners, as well as submitting and scoring tasks.
    """

    def __init__(self, challenge_name: str, miner_docker_images: List[str]):
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
        self._build_challenge_image()
        self._run_challenge_container()

        challenges = [
            self._get_challenge_from_container()
            for _ in range(constants.N_CHALLENGES_PER_EPOCH)
        ]
        logs = {}
        miner_scores = {}
        for miner_docker_image in self.miner_docker_images:
            self.docker_client.containers.run(
                miner_docker_image,
                detach=True,
                environment={"CHALLENGE_NAME": self.challenge_name},
                ports=[constants.CHALLENGE_DOCKER_PORT],
            )
            for miner_input in challenges:
                miner_output = self._submit_challenge_to_miner(miner_input)
                score = self._score_challenge(miner_input, miner_output)
                miner_scores.setdefault(miner_docker_image, []).append(score)
                logs.setdefault(miner_docker_image, []).append(
                    miner_input, miner_output, score
                )
        return miner_scores, logs

    def _build_challenge_image(self):
        """
        Builds the Docker image for the challenge using the provided challenge name.
        This step is necessary to create the environment in which the challenge will run.
        """
        self.docker_client.images.build(
            path=f"scriptcurity_core/challenges/{self.challenge_name}",
            tag=self.challenge_name,
        )

    def _remove_challenge_image(self):
        """
        Removes the Docker image for the challenge, identified by the challenge name.
        This is useful for cleanup after the challenge has been completed.
        """
        self.docker_client.images.remove(self.challenge_name)

    def _run_challenge_container(self):
        """
        Runs the Docker container for the challenge using the built image.
        The container runs in detached mode and listens on the port defined by constants.
        """
        self.docker_client.containers.run(
            self.challenge_name,
            detach=True,
            ports=[constants.CHALLENGE_DOCKER_PORT],
            name=self.challenge_name,
        )

    def _remove_challenge_container(self):
        """
        Stops and removes the Docker container running the challenge.
        This helps in cleaning up the environment after the challenge is done.
        """
        self.docker_client.containers.get(self.challenge_name).remove()

    def _submit_challenge_to_miner(self, challenge) -> dict:
        """
        Sends the challenge input to a miner by making an HTTP POST request to a local endpoint.
        The request submits the input, and the miner returns the generated output.

        Args:
            challenge: The input to be solved by the miner.

        Returns:
            A dictionary representing the miner's output.
        """
        response = httpx.post(
            "http://localhost:10002/solve",
            json={
                "miner_input": challenge,
            },
        )
        return response.json()

    def _get_challenge_from_container(self):
        """
        Retrieves a challenge input from the running challenge container by making an HTTP POST request.
        The challenge container returns a task that will be sent to the miners.

        Returns:
            A dictionary representing the challenge input.
        """
        response = httpx.post("http://localhost:10001/task")
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
        response = httpx.post(
            "http://localhost:10001/score",
            json={
                "miner_input": miner_input,
                "miner_output": miner_output,
            },
        )
        return response.json()
