import traceback

import bittensor as bt


from redteam_core.challenge_pool import docker_utils
from redteam_core.challenge_pool.controller import Controller
from redteam_core.constants import constants
from redteam_core.validator.models import (
    ComparisonLog,
    MinerChallengeCommit,
    ScoringLog,
)


class HBController(Controller):
    # Class-level cache for baseline reference comparison commits
    _baseline_reference_cache: dict[str, MinerChallengeCommit] = (
        {}
    )  # {docker_hub_id: MinerChallengeCommit}

    """
    A specialized controller for the 'humanize_behaviour_v3' challenge.
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
        Initializes the HBController, extending the original Controller.
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
            if docker_hub_id in HBController._baseline_reference_cache:
                cached_commit = HBController._baseline_reference_cache[docker_hub_id]
                # Verify it has scoring logs (i.e., has been successfully scored)
                if cached_commit.scoring_logs:
                    bt.logging.info(
                        f"[CONTROLLER - HBController] Reference commit {docker_hub_id} has already been scored, skipping"
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

        for reference_commit in self.baseline_reference_comparison_commits_to_score:
            try:
                bt.logging.info(
                    f"[CONTROLLER - HBController] Getting baseline reference: {reference_commit.docker_hub_id}"
                )
                self._setup_miner_container(reference_commit)

                self._generate_scoring_logs(reference_commit, challenge_inputs)

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
                    f"[CONTROLLER - HBController] Baseline reference scoring logs: {len(reference_commit.scoring_logs)}"
                )

                HBController._baseline_reference_cache[
                    reference_commit.docker_hub_id
                ] = reference_commit

            except Exception as e:
                bt.logging.error(
                    f"Error scoring baseline reference comparison, docker_hub_id: {reference_commit.docker_hub_id}: {e}"
                )
                bt.logging.error(traceback.format_exc())

        # Score commits and build comparison logs
        for miner_commit in self.miner_commits:
            uid, hotkey = miner_commit.miner_uid, miner_commit.miner_hotkey

            try:
                self._setup_miner_container(miner_commit)

                self._generate_scoring_logs(miner_commit, challenge_inputs)

                self._run_reference_comparison_inputs(miner_commit, challenge_inputs)

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

    def _score_miner_with_new_inputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ):
        """Run and score miner with new challenge inputs."""
        for i, miner_input in enumerate(challenge_inputs):
            # Skip if comparison result is high
            _higest_comparison_score = miner_commit.get_higest_comparison_score()
            if _higest_comparison_score >= 0.6 or _higest_comparison_score == 0.0:
                bt.logging.info(
                    f"[CONTROLLER - HBController] Skipping scoring for miner {miner_commit.miner_hotkey} on task {i} due to high comparison score: {_higest_comparison_score}"
                )
                miner_commit.scoring_logs[0].score = 0.0
                miner_commit.scoring_logs[0].error = (
                    "[Not Accepted]High comparison score, skipping scoring"
                )
                continue

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

    def _get_all_reference_commits(self):
        return self.reference_comparison_commits + list(
            HBController._baseline_reference_cache.values()
        )

    def _exclude_output_keys(self, miner_output: dict, reference_output: dict):
        miner_output["bot_py"] = None
        reference_output["bot_py"] = None
        return
