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

        self.max_similarity = 0.6
        self.min_similarity = 0
        self.min_score = 0.1
        self.break_point = 0.87
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

                    # def inverse_easePolyOut_exponent(y: float, exponent: float = 0.600) -> float:
                    #     """
                    #     Inverse of the polynomial ease-out function.

                    #     Args:
                    #         y (float): Eased value between 0 and 1.
                    #         exponent (float): The same exponent used in the original ease function.

                    #     Returns:
                    #         float: Original time value t.
                    #     """
                    #     if y < 0 or y > 1:
                    #         raise ValueError("y must be in the range [0, 1]")
                    #     return 1 - (1 - y) ** (1 / exponent)


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
            miner_commit
            miner_commit.accepted = (
                miner_commit.penalty >= self.min_similarity
                and miner_commit.penalty <= self.break_point
                and miner_commit.score >= self.min_score
            )

            ### UPDATE MINER SCORE BASED ON SIMILARITY SCORE
            miner_commit.score = self._adjust_score_by_similarity(
                miner_commit.score, miner_commit.penalty
            )

            # Update miner's best submission if current score is higher

            miner_commit.scored_timestamp = time.time()
            print(f"[HBChallengeManager] miner_commit: {miner_commit.scored_timestamp}")
            miner_state = self.miner_states[miner_commit.miner_uid]
            miner_state.update_best_commit(miner_commit)

            # Try to add to unique solutions set if commit is accepted
            if miner_commit.accepted and miner_commit.encrypted_commit:
                self._try_add_unique_commit(
                    encrypted_commit=miner_commit.encrypted_commit,
                    score=miner_commit.score,
                    docker_hub_id=miner_commit.docker_hub_id,
                )

            # Mark docker_hub_id as scored after successful scoring
            self._unique_scored_docker_hub_ids.add(miner_commit.docker_hub_id)

    def _ease_circle_in_out_shifted(self, x):
        x = x**3
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

    def _calculate_decayed_score(self, submission_timestamp, evaluation_timestamp, initial_score):
        """Calculate the final score with parabolic decay."""
        days_elapsed = (evaluation_timestamp - submission_timestamp) / 86400

        if days_elapsed <= self.stable_period_days:
            return initial_score
        elif days_elapsed <= self.expiration_days:
            decay_progress = (days_elapsed - self.stable_period_days) / (self.expiration_days - self.stable_period_days)
            decay_factor = 1 - decay_progress**2
            return initial_score * decay_factor
        else:
            return 0

    def _apply_softmax(self, scores):
        """Apply softmax with custom temperature to scores."""
        if np.sum(scores) == 0:
            return scores
        scaled_scores = scores / self.reward_temperature
        max_score = np.max(scaled_scores)
        scores_exp = np.exp(scaled_scores - max_score)
        return scores_exp / np.sum(scores_exp)

    def get_challenge_scores(self):
        """Calculate final scores for all miners matching the original implementation."""
        print("[HBChallengeManager] Running get challenge scores")
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        scores = np.zeros(len(uids))


        evaluation_timestamp = None
        for _, miner_state in self.miner_states.items():
            if (
                miner_state.miner_uid in uids
                and miner_state.miner_hotkey in self.metagraph.hotkeys
                and miner_state.best_commit is not None
                and miner_state.best_commit.scored_timestamp is not None
            ):
                if (
                    evaluation_timestamp is None
                    or miner_state.best_commit.scored_timestamp > evaluation_timestamp
                ):
                    evaluation_timestamp = miner_state.best_commit.scored_timestamp

        # If no valid scored_timestamp found, we can't apply time decay
        if evaluation_timestamp is None:
            bt.logging.warning(
                "No valid scored_timestamp found, cannot apply time decay"
            )

            # Fall back to regular scoring without time decay
            for _, miner_state in self.miner_states.items():
                if (
                    miner_state.miner_uid in uids
                    and miner_state.miner_hotkey in self.metagraph.hotkeys
                    and miner_state.best_commit is not None
                ):
                    scores[miner_state.miner_uid] = miner_state.best_commit.score

        # Step 1: Calculate decayed scores
        decayed_scores = []
        for _, miner_state in self.miner_states.items():
            best_commit = miner_state.best_commit
            if best_commit is None:
                continue

            initial_score = best_commit.score
            commit_timestamp = best_commit.scored_timestamp
            print(f'[commit_timestamp]type is {type(commit_timestamp)}', commit_timestamp)
            print(f'[evaluation_timestamp]type is {type(evaluation_timestamp)}', evaluation_timestamp)
            days_elapsed = (evaluation_timestamp - commit_timestamp) / 86400

            # Apply parabolic decay first
            decayed_score = self._calculate_decayed_score(commit_timestamp, evaluation_timestamp, initial_score)
            decayed_scores.append((miner_state.miner_uid, decayed_score, days_elapsed))

        # Step 2: Calculate adjusted scores with time factor saturation
        for miner_uid, decayed_score, days_elapsed in decayed_scores:
            adjusted_score = self._adjusted_score(decayed_score, days_elapsed)
            scores[miner_uid] = adjusted_score

print("scores: ", scores)
        # Step 3: Apply softmax to scores
        final_scores = self._apply_softmax(scores)
        print("=" * 50)
        print("[HBChallengeManager] Final scores:", final_scores)

        return final_scores