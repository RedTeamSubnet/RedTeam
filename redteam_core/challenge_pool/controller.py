from abc import abstractmethod
import copy
import time
from typing import Union
import traceback

import bittensor as bt
import docker
import docker.types
import requests

from redteam_core.challenge_pool.base import BaseController
from redteam_core.challenge_pool import docker_utils
from redteam_core.validator.models import (
    MinerChallengeCommit,
    ScoringLog,
    ComparisonLog,
)
from redteam_core.constants import constants


class Controller(BaseController):
    """
    A class to manage the lifecycle of a challenge, including the initialization
    of Docker containers for the challenge and miners, as well as submitting and scoring tasks.
    """

    def __init__(
        self,
        challenge_name: str,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
        reference_comparison_commits: list[MinerChallengeCommit],
        seed_inputs: list[dict] = [],
    ):
        """
        Initializes the Controller with the name of the challenge and the list of miner Docker images.
        Also sets up the Docker client for interacting with Docker containers.

        Args:
            challenge_name: The name of the challenge to be executed.
            miner_docker_images: A list of Docker images to be used for the miners.
        """
        super(Controller, self).__init__(
            challenge_name,
            challenge_info,
            miner_commits,
            reference_comparison_commits,
            seed_inputs,
        )
        self.docker_client = docker_utils.create_docker_client()

        self.local_network = "redteam_local"

        self.max_self_comparison_score = self.challenge_info["comparison_config"].get(
            "max_self_comparison_score", 0.9
        )
        # Add baseline image to compare with miners
        baseline_image = self.challenge_info.get("baseline", None)
        self.baseline_commit = MinerChallengeCommit(
            miner_uid=-1,
            miner_hotkey="baseline",
            docker_hub_id=baseline_image if baseline_image else None,
            challenge_name=challenge_name,
        )

    def start_challenge(self):
        """
        Initiates the challenge lifecycle by setting up and executing the challenge Docker container.

        This process involves:
        1. Building and running the challenge container within an isolated Docker network.
        2. Generating or retrieving challenge inputs to evaluate miners.
        3. Scoring a baseline Docker image, if specified, to establish a reference point.
        4. Iteratively running each miner's Docker container to submit and score their solutions.
        5. Collecting and logging the results, including any errors encountered during execution.
        6. Cleaning up Docker resources to ensure no residual containers or images remain.

        The method ensures that each miner's submission is evaluated against the challenge inputs,
        and comparison logs are generated to assess performance relative to reference commits.
        """
        # Setup challenge, get challenge container and network ready
        self._setup_challenge()

        # Generate new input to score miners
        num_task = self.challenge_info.get(
            "num_tasks", constants.N_CHALLENGES_PER_EPOCH
        )
        # Start with seed inputs and generate more if needed to reach num_task
        challenge_inputs = self.seed_inputs.copy()
        remaining_tasks = max(0, num_task - len(challenge_inputs))
        if remaining_tasks > 0:
            challenge_inputs.extend(
                [self._get_challenge_from_container() for _ in range(remaining_tasks)]
            )

        # Score baseline first if it exists
        if self.baseline_commit.docker_hub_id:
            try:
                self._setup_miner_container(self.baseline_commit)
                self._score_miner_with_new_inputs(
                    self.baseline_commit, challenge_inputs
                )
                docker_utils.remove_container_by_port(
                    client=self.docker_client,
                    port=constants.MINER_DOCKER_PORT,
                )
                docker_utils.clean_docker_resources(
                    client=self.docker_client,
                    remove_containers=True,
                    remove_images=True,
                )
            except Exception as e:
                bt.logging.error(f"Error scoring baseline: {e}")
                bt.logging.error(traceback.format_exc())

        # Score commits with new input and collect comparison logs
        for miner_commit in self.miner_commits:
            uid, hotkey = miner_commit.miner_uid, miner_commit.miner_hotkey

            try:
                bt.logging.info(
                    f"[CONTROLLER] Scoring miner {uid} - {hotkey} with commit {miner_commit.encrypted_commit}"
                )
                # 1. Validate and setup miner container
                self._setup_miner_container(miner_commit)

                # 2. Score with new inputs
                self._score_miner_with_new_inputs(miner_commit, challenge_inputs)

                # 3. Run reference comparisons
                self._run_reference_comparison_inputs(miner_commit)

            except Exception as e:
                bt.logging.error(f"Error while processing miner {uid} - {hotkey}: {e}")
                bt.logging.error(traceback.format_exc())
                if uid != self.baseline_commit.miner_uid:
                    miner_commit.scoring_logs.append(
                        ScoringLog(
                            miner_input=None,
                            miner_output=None,
                            score=0,
                            error=str(e),
                        )
                    )

            # Clean up miner container
            docker_utils.remove_container_by_port(
                client=self.docker_client,
                port=constants.MINER_DOCKER_PORT,
            )
            docker_utils.clean_docker_resources(
                client=self.docker_client,
                remove_containers=True,
                remove_images=True,
            )

        # Clean up challenge container
        docker_utils.remove_container(
            client=self.docker_client,
            container_name=self.challenge_name,
            stop_timeout=10,
            force=True,
            remove_volumes=True,
        )
        docker_utils.clean_docker_resources(
            client=self.docker_client,
            remove_containers=True,
            remove_images=True,
        )

    def _setup_challenge(self):
        """
        Sets up the challenge environment by building and running the challenge container
        in an isolated Docker network. Includes building the image, creating the network,
        and verifying the container's health status.
        """
        # Build challenge image
        docker_utils.build_challenge_image(
            client=self.docker_client,
            challenge_name=self.challenge_name,
            build_path=f"redteam_core/challenge_pool/{self.challenge_name}",
        )

        # Remove existing challenge container
        docker_utils.remove_container(
            client=self.docker_client,
            container_name=self.challenge_name,
            stop_timeout=10,
            force=True,
            remove_volumes=True,
        )

        # Create network
        docker_utils.create_network(
            client=self.docker_client,
            network_name=self.local_network,
            allow_internet=False,
        )

        # Run challenge container
        self.challenge_container = docker_utils.run_container(
            client=self.docker_client,
            image=self.challenge_name,
            detach=True,
            ports={
                f"{constants.CHALLENGE_DOCKER_PORT}/tcp": constants.CHALLENGE_DOCKER_PORT
            },
            **self.challenge_info.get("challenge_container_run_kwargs", {}),
        )
        bt.logging.info(
            f"[CONTROLLER] Challenge container started: {self.challenge_container.status}"
        )

        # Check challenge container health
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)
        docker_utils.check_container_alive(
            container=self.challenge_container,
            health_port=constants.CHALLENGE_DOCKER_PORT,
            protocol=_protocol,
            ssl_verify=_ssl_verify,
        )

    def _setup_miner_container(self, miner_commit: MinerChallengeCommit):
        """Setup and validate miner container. Raises if validation or setup fails."""

        if not docker_utils.is_image_digest_format_valid(miner_commit.docker_hub_id):
            raise ValueError(
                f"Invalid image format: {miner_commit.docker_hub_id}. Must include a SHA256 digest."
            )

        docker_utils.remove_container_by_port(
            client=self.docker_client,
            port=constants.MINER_DOCKER_PORT,
        )

        bt.logging.info(
            f"[CONTROLLER] Running miner {miner_commit.miner_uid} - {miner_commit.docker_hub_id}"
        )

        miner_start_time = (
            time.time()
            if miner_commit.miner_uid != self.baseline_commit.miner_uid
            else None
        )
        miner_container = docker_utils.run_container(
            client=self.docker_client,
            image=miner_commit.docker_hub_id,
            detach=True,
            ports={f"{constants.MINER_DOCKER_PORT}/tcp": constants.MINER_DOCKER_PORT},
            **self.challenge_info.get("miner_container_run_kwargs", {}),
        )

        # Check miner container health
        _protocol, _ssl_verify = self._check_protocol(is_challenger=False)
        docker_utils.check_container_alive(
            container=miner_container,
            health_port=constants.MINER_DOCKER_PORT,
            protocol=_protocol,
            ssl_verify=_ssl_verify,
            timeout=self.challenge_info.get("docker_run_timeout", 600),
            start_time=miner_start_time,
        )

    def _score_miner_with_new_inputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        """Run and score miner with new challenge inputs."""
        for i, miner_input in enumerate(challenge_inputs):
            miner_output, error_message = self._submit_challenge_to_miner(miner_input)
            score = (
                self._score_challenge(
                    miner_input=miner_input,
                    miner_output=miner_output,
                    task_id=i,
                )
                if miner_output is not None
                else 0.0
            )

            log = ScoringLog(
                miner_input=miner_input,
                miner_output=miner_output,
                score=score,
                error=error_message,
            )

            # Handle baseline scoring separately
            if miner_commit.miner_hotkey == "baseline":
                self.baseline_commit.scoring_logs.append(log)
            else:
                # Adjust score relative to baseline if baseline exists and has been scored
                if (
                    self.baseline_commit.docker_hub_id
                    and len(self.baseline_commit.scoring_logs) > i
                ):
                    log.score -= self.baseline_commit.scoring_logs[i].score
                    log.baseline_score = self.baseline_commit.scoring_logs[i].score
                miner_commit.scoring_logs.append(log)

    def _run_reference_comparison_inputs(self, miner_commit: MinerChallengeCommit):
        """
        Run miner with reference comparison commits inputs to compare performance.
        This method handles both baseline reference cache and similarity scoring.
        """

        # Get all reference commits including baseline cache if available
        current_commits_to_compare = self._get_current_commits_to_compare(
            miner_commit=miner_commit
        )
        reference_commits = (
            self._get_all_reference_commits() + current_commits_to_compare
        )

        for reference_commit in reference_commits:
            bt.logging.info(
                f"[CONTROLLER] Running comparison with reference commit {reference_commit.docker_hub_id}"
            )

            if not reference_commit.docker_hub_id in miner_commit.comparison_logs:
                miner_commit.comparison_logs[reference_commit.docker_hub_id] = []

            for reference_log in reference_commit.scoring_logs:
                if (
                    reference_log.miner_input is None
                    or reference_log.miner_output is None
                    or not miner_commit.scoring_logs
                    or miner_commit.scoring_logs[0].miner_output is None
                ):
                    bt.logging.warning(
                        f"[CONTROLLER] Skipping comparison with {reference_commit.docker_hub_id} for miner because the reference log is missing input or output."
                    )
                    continue

                _miner_output = miner_commit.scoring_logs[0].miner_output.copy()
                _reference_output = reference_log.miner_output.copy()

                _compare_result = self._compare_outputs(
                    miner_input=reference_log.miner_input,
                    miner_output=_miner_output,
                    reference_output=_reference_output,
                )
                _similarity_score = _compare_result.get("similarity_score", 1.0)
                _similarity_reason = _compare_result.get("reason", "Unknown")

                self._exclude_output_keys(_miner_output, _reference_output)

                if (
                    miner_commit.miner_hotkey == reference_commit.miner_hotkey
                    and _similarity_score < self.max_self_comparison_score
                ):
                    bt.logging.warning(
                        f"[CONTROLLER] Skipping self-comparison for {miner_commit.miner_hotkey} with {reference_commit.miner_hotkey} due to low similarity score {_similarity_score}"
                    )
                    continue

                comparison_log = ComparisonLog(
                    miner_input=reference_log.miner_input,
                    miner_output=_miner_output,
                    reference_output=_reference_output,
                    reference_hotkey=reference_commit.miner_hotkey,
                    reference_similarity_score=reference_commit.penalty,
                    similarity_score=_similarity_score,
                    reason=_similarity_reason,
                )

                miner_commit.comparison_logs[reference_commit.docker_hub_id].append(
                    comparison_log
                )

            if (
                reference_commit.docker_hub_id in miner_commit.comparison_logs
                and not miner_commit.comparison_logs[reference_commit.docker_hub_id]
            ):
                bt.logging.info(
                    f"[CONTROLLER] Removing empty comparison logs for {reference_commit.docker_hub_id} for miner."
                )
                del miner_commit.comparison_logs[reference_commit.docker_hub_id]
        return

    def _generate_scoring_logs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        """Run and score miner with new challenge inputs."""
        for miner_input in challenge_inputs:
            miner_output, error_message = self._submit_challenge_to_miner(miner_input)

            if miner_output is None or error_message:
                bt.logging.warning(
                    f"[CONTROLLER - ABSController] Miner {miner_commit.miner_hotkey} failed to produce output for reference comparison: {error_message}"
                )
                miner_commit.scoring_logs.insert(
                    0,
                    ScoringLog(
                        miner_input=miner_input,
                        miner_output=None,
                        error=(
                            f"[Not Accepted] {error_message}"
                            if error_message
                            else "[Not Accepted] No output from miner"
                        ),
                    ),
                )
                continue
            miner_commit.scoring_logs.insert(
                0,
                ScoringLog(
                    miner_input=miner_input,
                    miner_output=miner_output,
                    error=error_message,
                ),
            )

    def _compare_outputs(
        self, miner_input: dict, miner_output: dict, reference_output: dict
    ) -> dict:
        """
        Send comparison request to challenge container's /compare endpoint.

        Args:
            miner_input: The input used for both outputs
            miner_output: The output from the current miner
            reference_output: The output from the reference miner

        Returns:
            dict: Comparison score between 0 and 1, and reason for the score
        """
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)

        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
                "reference_output": reference_output,
            }

            response = requests.post(
                f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/compare",
                timeout=self.challenge_info.get("challenge_compare_timeout", 60),
                verify=_ssl_verify,
                json=payload,
            )

            response_data = response.json()
            data = response_data.get("data", {})
            similarity_score = data.get("similarity_score", 1.0)
            similarity_reason = data.get("reason", "Unknown")

            # Normalize score to float between 0 and 1
            if isinstance(similarity_score, int):
                similarity_score = float(similarity_score)
            elif not isinstance(similarity_score, float):
                similarity_score = 1.0

            return {"similarity_score": similarity_score, "reason": similarity_reason}

        except Exception as e:
            bt.logging.error(f"Error in comparison request: {str(e)}")
            return {"similarity_score": 0.0, "reason": f"Error: {str(e)}"}

    def _submit_challenge_to_miner(self, challenge_input) -> tuple[dict, str]:
        """
        Sends the challenge input to a miner by making an HTTP POST request to a local endpoint.
        The request submits the input, and the miner returns the generated output.

        Args:
            challenge: The input to be solved by the miner.

        Returns:
            A dictionary representing the miner's output.
        """

        error_message = ""
        miner_input = copy.deepcopy(challenge_input)
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

            if not response.ok:
                error_message = f"HTTP {response.status_code}: {response.text}"
                bt.logging.warning(error_message)
                return None, error_message

            return response.json(), error_message
        except requests.exceptions.Timeout:
            error_message = "Timeout occurred while trying to solve challenge."
            bt.logging.error(error_message)
            return None, error_message
        except Exception as ex:
            error_message = f"Submit challenge to miner failed: {str(ex)}"
            bt.logging.error(error_message)
            return None, error_message

    def _get_challenge_from_container(self) -> dict:
        """
        Retrieves a challenge input from the running challenge container by making an HTTP POST request.
        The challenge container returns a task that will be sent to the miners.
        Will retry up to 3 times if request fails.

        Returns:
            A dictionary representing the challenge input.

        Raises:
            Exception: If all retry attempts fail
        """
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)
        url = f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/task"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, verify=_ssl_verify)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(
                        f"Failed to get challenge after {max_retries} attempts: {str(e)}"
                    )

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
            bt.logging.debug(f"[CONTROLLER] Scoring payload: {str(payload)[:100]}...")
            response = requests.post(
                f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/score{_reset_query}",
                verify=_ssl_verify,
                json=payload,
            )
            score = response.json()
        except Exception as ex:
            bt.logging.error(f"Score challenge failed: {str(ex)}")
            score = 0.0

        if isinstance(score, int):
            score = float(score)
        elif not isinstance(score, float):
            score = 0.0
        return score

    def _check_protocol(
        self, is_challenger: bool = True
    ) -> tuple[str, Union[bool, None]]:
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

    def _get_current_commits_to_compare(
        self, miner_commit: MinerChallengeCommit = None
    ) -> list[MinerChallengeCommit]:
        _all_current_commits = []
        for commit in self.miner_commits:
            if commit.scoring_logs and (commit.miner_uid != miner_commit.miner_uid):
                _all_current_commits.append(commit)
        return _all_current_commits

    @abstractmethod
    def _get_all_reference_commits(self) -> list[MinerChallengeCommit]:
        """
        Get all reference commits including baseline cache if available.
        Override in specialized controllers to add their baseline cache.
        """
        return self.reference_comparison_commits

    @abstractmethod
    def _exclude_output_keys(self, miner_output: dict, reference_output: dict):
        """
        Exclude specific keys from outputs to prevent database bloat.
        Override in specialized controllers to specify which keys to exclude.
        """
        # Default implementation - no exclusions
        pass
