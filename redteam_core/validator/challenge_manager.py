import heapq
from typing import Optional

import bittensor as bt
import numpy as np

from redteam_core.validator.models import ScoringLog, MinerChallengeCommit


class MinerChallengeInfo:
    """
    Holds the state of a miner for a specific challenge.

    Attributes:
        miner_uid (int): Miner's UID
        miner_hotkey (str): Miner's current hotkey
        challenge_name (str): Name of the challenge
        latest_commit (Optional[MinerChallengeCommit]): Latest commit data
        best_commit (Optional[MinerChallengeCommit]): Best performing commit data
        daily_scores (dict[str, float]): Daily scores indexed by date
    """

    def __init__(self, miner_uid: int, miner_hotkey: str, challenge_name: str):
        self.miner_uid = miner_uid
        self.miner_hotkey = miner_hotkey
        self.challenge_name = challenge_name
        self.latest_commit: Optional[MinerChallengeCommit] = None
        self.best_commit: Optional[MinerChallengeCommit] = None
        self.daily_scores: dict[str, float] = {}

    def update_best_commit(self, miner_commit: MinerChallengeCommit):
        """
        Updates the best commit if the new commit is accepted and has a higher score.

        Args:
            commit: New commit to evaluate
        """
        if not miner_commit.accepted:
            return

        if self.best_commit is None or miner_commit.score > self.best_commit.score:
            self.best_commit = miner_commit


class ChallengeManager:
    """
    Manages a single challenge, including miners' submissions, scores, records and unique solutions set for comparison.
    """

    def __init__(self, challenge_info: dict, metagraph: bt.metagraph):
        self.challenge_info = challenge_info
        self.challenge_name = challenge_info["name"]
        self.challenge_incentive_weight = challenge_info["challenge_incentive_weight"]
        self.metagraph = metagraph

        # Track unique solutions set using cache keys
        self.max_unique_commits = challenge_info["max_unique_commits"]
        self._unique_commits_heap: list[
            tuple[float, str]
        ] = []  # [(score, encrypted_commit)]
        self._unique_commits_set: set[str] = (
            set()
        )  # For O(1) lookup of existing commits

        # Miner states, mapping from uid to miner state
        self.miner_states: dict[int, MinerChallengeInfo] = {}

    def update_miner_infos(self, miner_commits: list[MinerChallengeCommit]):
        """
        Update miner infos based on new submissions.
        If an UID 's hotkey changes, a new miner info will be created.

        Args:
            miner_commits (dict): Dictionary of miner submissions with UID and SS58 address as keys.
        """
        for miner_commit in miner_commits:
            current_miner_state: MinerChallengeInfo = self.miner_states.get(
                miner_commit.miner_uid,
                MinerChallengeInfo(
                    miner_uid=miner_commit.miner_uid,
                    miner_hotkey=miner_commit.miner_hotkey,
                    challenge_name=miner_commit.challenge_name,
                ),
            )

            if current_miner_state.miner_hotkey != miner_commit.miner_hotkey:
                # UID's hotkey has changed, create a new miner state
                self.miner_states[miner_commit.miner_uid] = MinerChallengeInfo(
                    miner_uid=miner_commit.miner_uid,
                    miner_hotkey=miner_commit.miner_hotkey,
                    challenge_name=miner_commit.challenge_name,
                )
                continue

            # Update miner state with latest submission
            current_miner_state.latest_commit = miner_commit

        # Remove miners not in metagraph using dict comprehension
        self.miner_states = {
            miner_uid: miner_state
            for miner_uid, miner_state in self.miner_states.items()
            if miner_state.miner_hotkey in self.metagraph.hotkeys
        }

    def update_miner_scores(self, miner_commits: list[MinerChallengeCommit]):
        """
        Update miners 's latest submission scores and penalties.

        Args:
            miner_scoring_logs (dict): Dictionary of miner scoring logs with UID and SS58 address as keys.
            miner_penalties (dict): Dictionary of miner penalties with UID and SS58 address as keys.
        """
        for miner_commit in miner_commits:
            # Mean score
            miner_commit.score = np.mean(
                [scoring_log.score for scoring_log in miner_commit.scoring_logs]
            ).item()

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

            miner_commit.accepted = miner_commit.penalty < self.challenge_info.get(
                "penalty_threshold", 0.5
            )

            # Update miner 's best submission if current score is higher
            miner_state = self.miner_states[miner_commit.miner_uid]
            miner_state.update_best_commit(miner_commit)

    def _try_add_unique_commit(self, encrypted_commit: str, score: float):
        """
        Adds a new commit to the unique commits collection if it qualifies.

        Args:
            encrypted_commit: The encrypted commit string to add
            score: The score of the commit
        """
        # Skip if we already have this commit
        if encrypted_commit in self._unique_commits_set:
            return

        if len(self._unique_commits_heap) < self.max_unique_commits:
            # Still have room, add directly
            heapq.heappush(self._unique_commits_heap, (score, encrypted_commit))
            self._unique_commits_set.add(encrypted_commit)
        elif score > self._unique_commits_heap[0][0]:
            # Score is better than our worst commit, replace it
            _, old_commit = heapq.heapreplace(
                self._unique_commits_heap, (score, encrypted_commit)
            )
            self._unique_commits_set.remove(old_commit)
            self._unique_commits_set.add(encrypted_commit)

    def get_unique_commits(self) -> set[str]:
        return self._unique_commits_set

    def get_challenge_scores(self):
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        scores = np.zeros(len(uids))

        for _, miner_state in self.miner_states.items():
            if miner_state.miner_uid in uids and miner_state.best_commit is not None:
                scores[miner_state.miner_uid] = miner_state.best_commit.score

        # Apply softmax
        temperature = self.challenge_info.get("temperature", 0.2)
        scaled_scores = scores / temperature
        scores_exp = np.exp(scaled_scores - np.max(scaled_scores))
        softmax_scores = scores_exp / np.sum(scores_exp)

        return softmax_scores
