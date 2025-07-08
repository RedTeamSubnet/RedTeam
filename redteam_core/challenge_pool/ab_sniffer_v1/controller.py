import traceback
import time

import bittensor as bt
import numpy as np
import requests


from redteam_core.challenge_pool import docker_utils
from redteam_core.challenge_pool.controller import Controller
from redteam_core.constants import constants
from redteam_core.validator.models import (
    ComparisonLog,
    MinerChallengeCommit,
    ScoringLog,
)


class ABSController(Controller):
    # Class-level cache for baseline reference comparison commits
    _baseline_reference_cache: dict[str, MinerChallengeCommit] = (
        {}
    )  # {docker_hub_id: MinerChallengeCommit}

    """
    A specialized controller for the 'ab_sniffer_v1' challenge.
    Inherits from the base Controller and modifies specific logic.
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
        Initializes the ABSController, extending the original Controller.
        """
        super().__init__(
            challenge_name,
            challenge_info,
            miner_commits,
            reference_comparison_commits,
            seed_inputs,
        )

        self.behavior_scaling_factor = self.challenge_info.get(
            "behavior_scaling_factor", 0.1
        )

        # Get baseline reference comparison docker hub IDs from challenge info
        self.baseline_reference_comparison_docker_hub_ids = self.challenge_info.get(
            "baseline_reference_comparison_docker_hub_ids", []
        )

        # Initialize local storage for this instance
        self.baseline_reference_comparison_commits_to_score: list[
            MinerChallengeCommit
        ] = []

        for docker_hub_id in self.baseline_reference_comparison_docker_hub_ids:
            # Check if this docker_hub_id is already in the class cache
            if docker_hub_id in ABSController._baseline_reference_cache:
                cached_commit = ABSController._baseline_reference_cache[docker_hub_id]
                # Verify it has scoring logs (i.e., has been successfully scored)
                if cached_commit.scoring_logs:
                    bt.logging.info(
                        f"[CONTROLLER - ABSController] Reference commit {docker_hub_id} has already been scored, skipping"
                    )
                    continue

            # If not in cache or not scored, add to list of commits to score
            # Create a new commit object
            new_commit = MinerChallengeCommit(
                miner_uid=-1,
                miner_hotkey="baseline-reference",
                challenge_name=self.challenge_name,
                docker_hub_id=docker_hub_id,
            )

            # Add to our instance list
            self.baseline_reference_comparison_commits_to_score.append(new_commit)

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
        bt.logging.debug(
            f"[CONTROLLER - ABSController] Starting ABSController challenge with {len(self.baseline_reference_comparison_commits_to_score)} baseline references to score"
        )

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

        bt.logging.debug(
            f"[CONTROLLER - ABSController] Generated {len(challenge_inputs)} challenge inputs"
        )

        bt.logging.info(
            f"[CONTROLLER - ABSController] Starting baseline reference scoring for {len(self.baseline_reference_comparison_commits_to_score)} references"
        )

        # Score baseline reference comparisons (only those that need scoring)
        for reference_commit in self.baseline_reference_comparison_commits_to_score:
            try:
                bt.logging.info(
                    f"[CONTROLLER - ABSController] Scoring baseline reference: {reference_commit.docker_hub_id}"
                )
                self._setup_miner_container(reference_commit)

                self._get_reference_outputs(reference_commit, challenge_inputs)

                docker_utils.remove_container_by_port(
                    client=self.docker_client,
                    port=constants.MINER_DOCKER_PORT,
                )
                docker_utils.clean_docker_resources(
                    client=self.docker_client,
                    remove_containers=True,
                    remove_images=False,
                )

                bt.logging.info(
                    f"[CONTROLLER - ABSController] Baseline reference scoring logs: {len(reference_commit.scoring_logs)}"
                )
                # Update the class cache with the scored commit
                ABSController._baseline_reference_cache[
                    reference_commit.docker_hub_id
                ] = reference_commit

            except Exception as e:
                bt.logging.error(
                    f"Error scoring baseline reference comparison, docker_hub_id: {reference_commit.docker_hub_id}: {e}"
                )
                bt.logging.error(traceback.format_exc())

        bt.logging.debug(
            f"[CONTROLLER - ABSController] Starting miner scoring for {len(self.miner_commits)} miners"
        )

        # Score commits with new input and collect comparison logs
        for miner_commit in self.miner_commits:
            uid, hotkey = miner_commit.miner_uid, miner_commit.miner_hotkey

            try:
                # 1. Validate and setup miner container
                self._setup_miner_container(miner_commit)

                # 2. Run reference comparisons
                self._run_reference_comparison_inputs(miner_commit, challenge_inputs)

                # 3. Score with new inputs
                self._score_miner_with_new_inputs(miner_commit, challenge_inputs)

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
                remove_images=False,
            )

        bt.logging.debug(
            f"[CONTROLLER - ABSController] Challenge completed, cleaning up challenge container"
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
            remove_images=False,
        )

    def _run_reference_comparison_inputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        # Skip for baseline commit since it's used as reference
        if miner_commit.miner_uid == self.baseline_commit.miner_uid:
            return

        all_reference_comparison_commits = self.reference_comparison_commits + list(
            ABSController._baseline_reference_cache.values()
        )
        miner_output, error_message = self._submit_challenge_to_miner(
            challenge_inputs[0]
        )

        if miner_output is None or error_message:
            bt.logging.warning(
                f"[CONTROLLER - ABSController] Miner {miner_commit.miner_hotkey} failed to produce output for reference comparison: {error_message}"
            )
            miner_commit.scoring_logs.insert(
                0,
                ScoringLog(
                    miner_input=challenge_inputs[0],
                    miner_output=None,
                    error=error_message,
                    log_time=time.time(),
                ),
            )
            return
        miner_commit.scoring_logs.insert(
            0,
            ScoringLog(
                miner_input=challenge_inputs[0],
                miner_output=miner_output,
                error=error_message,
                log_time=time.time(),
            ),
        )

        for reference_commit in all_reference_comparison_commits:
            bt.logging.info(
                f"[CONTROLLER - ABSController] Running comparison with reference commit {reference_commit.miner_uid}"
            )
            miner_commit.comparison_logs[reference_commit.docker_hub_id] = []
            # Process each input from the reference commit's scoring logs
            for _, reference_log in enumerate(reference_commit.scoring_logs):
                if (
                    reference_log.miner_input is None
                    or reference_log.miner_output is None
                ):
                    bt.logging.warning(
                        f"[CONTROLLER - ABSController] Skipping comparison with {reference_commit.docker_hub_id} for miner because the reference log is missing input or output."
                    )
                    continue
                _similarity_score = self._compare_outputs(
                    miner_input=reference_log.miner_input,
                    miner_output=miner_output,
                    reference_output=reference_log.miner_output,
                )

                # removing detection_js from comparison logs
                _miner_output = miner_output.copy()
                _reference_output = reference_log.miner_output.copy()
                _miner_output["detection_js"] = None
                _reference_output["detection_js"] = None

                comparison_log = ComparisonLog(
                    miner_input=reference_log.miner_input,
                    miner_output=_miner_output,
                    reference_output=_reference_output,
                    reference_hotkey=reference_commit.miner_hotkey,
                    reference_similarity_score=reference_commit.penalty,
                    similarity_score=_similarity_score,
                )

                # Add to comparison logs
                miner_commit.comparison_logs[reference_commit.docker_hub_id].append(
                    comparison_log
                )
            # Remove comparison logs if empty or None
            if (
                reference_commit.docker_hub_id in miner_commit.comparison_logs
                and not miner_commit.comparison_logs[reference_commit.docker_hub_id]
            ):
                bt.logging.info(
                    f"[CONTROLLER - ABSController] Removing empty comparison logs for {reference_commit.docker_hub_id} for miner."
                )
                del miner_commit.comparison_logs[reference_commit.docker_hub_id]
            bt.logging.info(
                f"[CONTROLLER - ABSController] Completed making `comparison_logs` with {reference_commit.docker_hub_id} for miner."
            )
        return

    def _get_reference_outputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        """Run and score miner with new challenge inputs."""
        for i, miner_input in enumerate(challenge_inputs):
            miner_output, error_message = self._submit_challenge_to_miner(miner_input)

            miner_output["log_time"] = time.time()

            log = ScoringLog(
                miner_input=miner_input,
                miner_output=miner_output,
                score=0.0,
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

    def _score_miner_with_new_inputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        """Run and score miner with new challenge inputs."""
        for i, miner_input in enumerate(challenge_inputs):
            # Skip if comparison result is high
            _higest_comparison_score = miner_commit.get_higest_comparison_score()

            if _higest_comparison_score >= 0.6 or _higest_comparison_score == 0.0:
                bt.logging.info(
                    f"[CONTROLLER - ABSController] Skipping scoring for miner {miner_commit.miner_hotkey} on task {i} due to high comparison score: {_higest_comparison_score}"
                )
                miner_commit.scoring_logs[0].score = 0.0
                miner_commit.scoring_logs[0].error = (
                    "[Not Accepted]High comparison score, skipping scoring"
                )

                continue

            # Score miner commit
            score = (
                self._score_challenge(
                    miner_input=miner_input,
                    miner_output=miner_commit.scoring_logs[0].miner_output,
                    task_id=i,
                )
                if miner_commit.scoring_logs[0].miner_output is not None
                else 0.0
            )

            miner_commit.scoring_logs[0].score = score

    def _compare_outputs(
        self, miner_input: dict, miner_output: dict, reference_output: dict
    ) -> float:
        """
        Send comparison request to challenge container's /compare endpoint.

        Args:
            miner_input: The input used for both outputs
            miner_output: The output from the current miner
            reference_output: The output from the reference miner

        Returns:
            float: Comparison score between 0 and 1
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

            # Normalize score to float between 0 and 1
            if isinstance(similarity_score, int):
                similarity_score = float(similarity_score)
            elif not isinstance(similarity_score, float):
                similarity_score = 1.0

            return max(0.0, min(1.0, similarity_score))

        except Exception as e:
            bt.logging.error(f"Error in comparison request: {str(e)}")
            return 0.0
