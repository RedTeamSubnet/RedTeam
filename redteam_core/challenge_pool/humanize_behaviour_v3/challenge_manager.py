import math
import traceback
import time

import bittensor as bt
import numpy as np

from redteam_core.validator.models import MinerChallengeCommit
from redteam_core.validator.challenge_manager import ChallengeManager


class HBChallengeManager(ChallengeManager):

    def __init__(self, challenge_info: dict, metagraph: bt.metagraph):
        super().__init__(challenge_info, metagraph)

        emission_config = self.challenge_info.get("emission_config", {})
        self.stable_period_days = emission_config.get("stable_period_days", 10)
        self.expiration_days = emission_config.get("expiration_days", 15)
        self.alpha = emission_config.get("alpha", 0.002)
        self.t_max = emission_config.get("t_max", 10)
        self.reward_temperature = emission_config.get("reward_temperature", 0.2)

        self.max_similarity = 0.4
        self.min_similarity = 0
        self.min_score = 0.1
        self.break_point = 0.6
        self.max_input = 1.0
        self.min_value = 0
        self.max_value = 1

    def update_miner_scores(self, miner_commits: list[MinerChallengeCommit]):
        """
        Update miners' latest submission scores and penalties.

        Args:
            miner_scoring_logs (dict): Dictionary of miner scoring logs with UID and SS58 address as keys.
            miner_penalties (dict): Dictionary of miner penalties with UID and SS58 address as keys.
        """

        bt.logging.info(
            f"[CHALLENGE MANAGER] Challenge {self.challenge_name}, updating miner scores and penalties"
        )

        for miner_commit in miner_commits:
            if miner_commit.docker_hub_id in self._unique_scored_docker_hub_ids:
                continue  # Skip if already scored

            if not miner_commit.scoring_logs:
                continue  # Skip if no scoring logs

            try:
                # Compute mean score
                score = np.mean(
                    [scoring_log.score for scoring_log in miner_commit.scoring_logs]
                ).item()
                if np.isnan(score):
                    miner_commit.score = 0.0
                else:
                    miner_commit.score = float(score)

                # Compute penalty
                if miner_commit.comparison_logs:
                    penalty_values = [
                        np.mean([log.similarity_score for log in logs])
                        for logs in miner_commit.comparison_logs.values()
                    ]
                    penalty = np.max(penalty_values).item() if penalty_values else 0
                    if np.isnan(penalty):
                        miner_commit.penalty = 0.0
                    else:
                        miner_commit.penalty = float(penalty)
                else:
                    miner_commit.penalty = 0.0

            except Exception as e:
                bt.logging.error(
                    f"[CHALLENGE MANAGER] Challenge {self.challenge_name}, "
                    f"failed to get commit {miner_commit.encrypted_commit} scores and penalties: {traceback.format_exc()}, {e}"
                )
                continue

            # Acceptance criteria
            miner_commit.accepted = (
                miner_commit.penalty >= self.min_similarity
                and miner_commit.penalty <= self.break_point
                and miner_commit.score >= self.min_score
            )

            ### Adjust scores
            miner_commit.score = self._adjust_score_by_similarity(
                miner_commit.score, miner_commit.penalty
            )

            # Update miner's best submission
            miner_commit.scored_timestamp = time.time()

            miner_state = self.miner_states[miner_commit.miner_uid]
            if miner_state:
                miner_state.update_best_commit(miner_commit)
                bt.logging.debug(
                    f"Updated best commit for miner {miner_commit.miner_uid}"
                )

            # Add to unique solutions if accepted
            if miner_commit.accepted and miner_commit.encrypted_commit:
                self._try_add_unique_commit(
                    encrypted_commit=miner_commit.encrypted_commit,
                    score=miner_commit.score,
                    docker_hub_id=miner_commit.docker_hub_id,
                )

            # Mark as scored
            self._unique_scored_docker_hub_ids.add(miner_commit.docker_hub_id)

    def get_challenge_scores(self):
        """Calculate final scores for all miners matching the original implementation."""
        n_uids = int(self.metagraph.n)
        scores = np.zeros(n_uids)

        evaluation_timestamp = None
        # Step 1: Determine latest evaluation timestamp & set initial scores
        for miner_state in self.miner_states.values():
            best_commit = miner_state.best_commit

            if (
                best_commit is None
                or miner_state.miner_uid >= n_uids
                or miner_state.miner_hotkey not in self.metagraph.hotkeys
            ):
                continue

            # Set initial scores
            scores[miner_state.miner_uid] = best_commit.score

            # Track the latest evaluation timestamp
            if (
                evaluation_timestamp is None
                or best_commit.scored_timestamp > evaluation_timestamp
            ):
                evaluation_timestamp = best_commit.scored_timestamp

        # Step 2: If no valid timestamp found, return unmodified scores
        if evaluation_timestamp is None:
            bt.logging.warning(
                "No valid scored_timestamp found, cannot apply time decay"
            )
            return self._apply_softmax(scores)

        # Step 3: Apply decay and adjustment
        for miner_state in self.miner_states.values():
            best_commit = miner_state.best_commit
            if (
                best_commit is None
                or miner_state.miner_uid >= n_uids
                or miner_state.miner_hotkey not in self.metagraph.hotkeys
            ):
                continue  # Skip invalid miners

            commit_timestamp = best_commit.scored_timestamp
            days_elapsed = (evaluation_timestamp - commit_timestamp) / 86400

            # Apply decay and adjustment
            decayed_score = self._calculate_decayed_score(
                commit_timestamp, evaluation_timestamp, best_commit.score
            )
            adjusted_score = self._adjusted_score(decayed_score, days_elapsed)

            # Update scores
            scores[miner_state.miner_uid] = adjusted_score

        # Step 4: Apply softmax and return final scores
        normalized_scores = [
            self._inverse_easePolyOut_exponent(score) for score in scores
        ]
        final_scores = self._apply_softmax(normalized_scores)
        return final_scores

    def _ease_circle_in_out_shifted(self, x):
        x = x**1.5
        if x < 0.5:
            return 0.5 * (1 - math.sqrt(1 - (2 * x) ** 2))
        return 0.5 * (math.sqrt(1 - (2 * x - 2) ** 2) + 1)

    def _scaling_from_similarity(self, x):
        if x <= self.break_point:
            t = (x - self.max_similarity) / (self.break_point - self.max_similarity)
            normalized_break = (self.break_point - self.max_similarity) / (
                self.max_input - self.max_similarity
            )
            eased_break = self._ease_circle_in_out_shifted(normalized_break)
            value_break = self.min_value + eased_break * (
                self.max_value - self.min_value
            )
            return self.min_value + t * (value_break - self.min_value)
        t = (x - self.max_similarity) / (self.max_input - self.max_similarity)
        return self.min_value + self._ease_circle_in_out_shifted(t) * (
            self.max_value - self.min_value
        )

    def _adjust_score_by_similarity(self, raw_score, similarity_score):
        """Adjusts the raw score based on the similarity score."""
        if similarity_score < self.min_similarity:
            return 0
        if similarity_score < self.max_similarity:
            return raw_score
        s = self._scaling_from_similarity(similarity_score)
        return raw_score * (1 - s)

    def _time_factor_saturating(self, t):
        """Returns e^(-alpha * t) up to t_max, then saturates."""
        effective_t = min(t, self.t_max)
        return math.exp(-self.alpha * effective_t)

    def _adjusted_score(self, raw_accuracy, t):
        """Computes the adjusted score considering time factor saturation."""
        return raw_accuracy * self._time_factor_saturating(t)

    def _calculate_decayed_score(
        self, submission_timestamp, evaluation_timestamp, initial_score
    ):
        """Calculate the final score with parabolic decay."""
        days_elapsed = (evaluation_timestamp - submission_timestamp) / 86400

        if days_elapsed <= self.stable_period_days:
            return initial_score
        elif days_elapsed <= self.expiration_days:
            decay_progress = (days_elapsed - self.stable_period_days) / (
                self.expiration_days - self.stable_period_days
            )
            decay_factor = 1 - decay_progress**2
            return initial_score * decay_factor
        else:
            return 0

    def _apply_softmax(self, scores):
        """Apply softmax with custom temperature to scores."""
        scores = np.asarray(scores)  # Convert to NumPy array
        if np.sum(scores) == 0:
            return scores
        scores = np.clip(scores, 0, None)
        scaled_scores = scores / self.reward_temperature
        max_score = np.max(scaled_scores)
        scores_exp = np.exp(scaled_scores - max_score)
        return scores_exp / np.sum(scores_exp)

    def _inverse_easePolyOut_exponent(self, y: float, exponent: float = 0.600) -> float:
        """Inverse of the polynomial ease-out function, y must be in the range [0, 1]."""
        if y < 0 or y > 1:
            raise ValueError("y must be in the range [0, 1]")
        return 1 - (1 - y) ** (1 / exponent)
