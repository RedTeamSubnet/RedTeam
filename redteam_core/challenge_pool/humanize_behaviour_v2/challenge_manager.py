import math
import heapq
import traceback

import bittensor as bt
import numpy as np

from redteam_core.validator.models import MinerChallengeCommit
from redteam_core.validator.challenge_manager import ChallengeManager


class HBChallengeManager(ChallengeManager):

    def __init__(self, challenge_info: dict, metagraph: bt.metagraph):
        super().__init__(challenge_info, metagraph)
        self.max_similarity = 0.6
        self.min_similarity = 0.15
        self.min_score = 0.1
        self.break_point = 0.87
        self.max_input = 1.0
        self.min_value = 0
        self.max_value = 1

    def update_miner_scores(self, miner_commits: list[MinerChallengeCommit]):
        """
        Update miners 's latest submission scores and penalties.

        Args:
            miner_scoring_logs (dict): Dictionary of miner scoring logs with UID and SS58 address as keys.
            miner_penalties (dict): Dictionary of miner penalties with UID and SS58 address as keys.
        """
        print("[HBChallengeManager] Updating miner scores and penalties")
        for miner_commit in miner_commits:
            if miner_commit.docker_hub_id in self._unique_scored_docker_hub_ids:
                # Skip if docker_hub_id has been scored
                continue

            try:
                if not miner_commit.scoring_logs:
                    # Skip if no scoring logs
                    continue
                else:
                    # Mean score
                    miner_commit.score = np.mean(
                        [scoring_log.score for scoring_log in miner_commit.scoring_logs]
                    ).item()

                if not miner_commit.comparison_logs:
                    # Penalty is 0 if no comparison logs
                    miner_commit.penalty = 0
                else:
                    # Penalty by max of mean similarity with unique solutions
                    miner_commit.penalty = np.max(
                        [
                            np.mean(
                                [
                                    comparison_log.similarity_score
                                    for comparison_log in comparison_logs
                                ]
                            )
                            for _, comparison_logs in miner_commit.comparison_logs.items()
                        ]
                    ).item()
            except Exception:
                bt.logging.error(
                    f"[CHALLENGE MANAGER] Challenge {self.challenge_name}, failed to get commit {miner_commit.encrypted_commit} scores and penalties: {traceback.format_exc()}"
                )
                continue

            miner_commit.accepted = (
                miner_commit.penalty >= self.min_similarity
                and miner_commit.penalty <= self.break_point
                and miner_commit.score >= self.min_score
            )

            ### UPDATE MINER SCORE BASED ON SIMILARITY SCORE
            miner_commit.score = self._adjust_score_by_similarity(miner_commit.score, miner_commit.penalty)

            # Update miner 's best submission if current score is higher
            miner_state = self.miner_states[miner_commit.miner_uid]
            miner_state.update_best_commit(miner_commit)

            # Try to add to unique solutions set if commit is accepted
            if miner_commit.accepted and miner_commit.encrypted_commit:
                self._try_add_unique_commit(
                    encrypted_commit=miner_commit.encrypted_commit,
                    score=miner_commit.score,
                    docker_hub_id=miner_commit.docker_hub_id,
                )

            # Mark as scored after successful scoring
            self._unique_scored_docker_hub_ids.add(miner_commit.docker_hub_id)

    def _ease_circle_in_out_shifted(self, x):
        x = x ** 3
        if x < 0.5:
            return 0.5 * (1 - math.sqrt(1 - (2 * x)**2))
        return 0.5 * (math.sqrt(1 - (2 * x - 2)**2) + 1)

    def _scaling_from_similarity(self, x):
        if x <= self.break_point:
            t = (x - self.max_similarity) / (self.break_point - self.max_similarity)
            normalized_break = (self.break_point - self.max_similarity) / (self.max_input - self.max_similarity)
            eased_break = self.ease_circle_in_out_shifted(normalized_break)
            value_break = self.min_value + eased_break * (self.max_value - self.min_value)
            return self.min_value + t * (value_break - self.min_value)
        t = (x - self.max_similarity) / (self.max_input - self.max_similarity)
        return self.min_value + self.ease_circle_in_out_shifted(t) * (self.max_value - self.min_value)

    def _adjust_score_by_similarity(self, raw_score, similarity_score):
        if similarity_score < self.min_similarity:
            return 0
        if similarity_score < self.max_similarity:
            return raw_score
        s = self.scaling_from_similarity(similarity_score)
        return raw_score * (1 - s)