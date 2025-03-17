import numpy as np
import time
from redteam_core.validator.challenge_manager import ChallengeManager

class ResponseQualityAdversarialChallengeManager(ChallengeManager):
    def get_challenge_scores(self):
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        scores = np.zeros(len(uids))

        current_time = time.time()
        decay_period = 14 * 24 * 60 * 60  # 14 days in seconds

        for _, miner_state in self.miner_states.items():
            if (
                miner_state.miner_uid in uids
                and miner_state.miner_hotkey in self.metagraph.hotkeys
                and miner_state.best_commit is not None
            ):
                commit = miner_state.best_commit
                time_elapsed = current_time - commit.scored_timestamp
                decay_factor = max(0, 1 - (time_elapsed / decay_period))
                scores[miner_state.miner_uid] = commit.score * decay_factor

        # Apply softmax
        temperature = self.challenge_info.get("temperature", 0.2)
        scaled_scores = scores / temperature
        scores_exp = np.exp(scaled_scores - np.max(scaled_scores))
        softmax_scores = scores_exp / np.sum(scores_exp)

        return softmax_scores