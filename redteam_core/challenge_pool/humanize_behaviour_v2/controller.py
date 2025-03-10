import bittensor as bt
import numpy as np

from redteam_core.challenge_pool.controller import Controller
from redteam_core.validator.models import (
    MinerChallengeCommit,
    ComparisonLog,
)

class HBController(Controller):
    """
    A specialized controller for the 'humanize_behaviour_v2' challenge.
    Inherits from the base Controller and modifies specific logic.
    """

    def __init__(
        self,
        challenge_name: str,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
        reference_comparison_commits: list[MinerChallengeCommit],
    ):
        """
        Initializes the HBController, extending the original Controller.
        """
        super().__init__(challenge_name, challenge_info, miner_commits, reference_comparison_commits)

        self.behavior_scaling_factor = self.challenge_info.get("behavior_scaling_factor", 0.1)

    def _run_reference_comparison_inputs(self, miner_commit: MinerChallengeCommit):
        # Skip for baseline commit since it's used as reference
        if miner_commit.miner_uid == self.baseline_commit.miner_uid:
            return

        for reference_commit in self.reference_comparison_commits:
            bt.logging.info(
                f"[CONTROLLER - HBController] Running comparison with reference commit {reference_commit.miner_uid}"
            )

            miner_mean_score = np.mean(
                [scoring_log.score for scoring_log in miner_commit.scoring_logs]
            ).item()

            # Skip if already compared, or if mean score is less than behavior scaling factor, or if miner is the same
            if reference_commit.docker_hub_id in miner_commit.comparison_logs or miner_mean_score < self.behavior_scaling_factor or miner_commit.miner_hotkey == reference_commit.miner_hotkey:
                continue
            else:
                miner_commit.comparison_logs[reference_commit.docker_hub_id] = []

            # Process each input from the reference commit's scoring logs
            for i, reference_log in enumerate(reference_commit.scoring_logs):
                if reference_log.miner_input is None:
                    continue

                # Submit the same input to current miner
                miner_output, error_message = self._submit_challenge_to_miner(
                    reference_log.miner_input
                )

                # Create comparison log
                comparison_log = ComparisonLog(
                    miner_input=reference_log.miner_input,
                    miner_output=miner_output,
                    reference_output=reference_log.miner_output,
                    error=error_message
                )

                # Add to comparison logs
                miner_commit.comparison_logs[reference_commit.docker_hub_id].append(comparison_log)
