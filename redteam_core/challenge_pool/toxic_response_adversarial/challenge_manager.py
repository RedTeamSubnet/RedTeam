import numpy as np
import time
from redteam_core.validator.challenge_manager import ChallengeManager

class ToxicResponseAdversarialChallengeManager(ChallengeManager):
    def get_challenge_scores(self):
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        scores = np.zeros(len(uids))

        current_time = time.time()
        decay_period = 5 * 24 * 60 * 60  # 5 days in seconds

        for _, miner_state in self.miner_states.items():
            if (
                miner_state.miner_uid in uids
                and miner_state.miner_hotkey in self.metagraph.hotkeys
                and miner_state.miner_hotkey == self.metagraph.hotkeys[miner_state.miner_uid]
            ):
                best_score = 0

                # Check best_commit if available
                if miner_state.best_commit is not None:
                    best_commit = miner_state.best_commit
                    time_elapsed = current_time - best_commit.scored_timestamp
                    decay_factor = max(0, 1 - (time_elapsed / decay_period))
                    best_score = best_commit.score * decay_factor

                # Compare with latest_commit if available
                if miner_state.latest_commit is not None and miner_state.latest_commit.accepted:
                    latest_commit = miner_state.latest_commit
                    time_elapsed = current_time - latest_commit.scored_timestamp
                    decay_factor = max(0, 1 - (time_elapsed / decay_period))
                    latest_score = latest_commit.score * decay_factor

                    # Use whichever is higher
                    best_score = max(best_score, latest_score)

                scores[miner_state.miner_uid] = best_score

        # Apply softmax
        temperature = self.challenge_info.get("temperature", 0.2)
        scaled_scores = scores / temperature
        scores_exp = np.exp(scaled_scores - np.max(scaled_scores))
        softmax_scores = scores_exp / np.sum(scores_exp)

        return softmax_scores