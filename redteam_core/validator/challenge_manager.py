import heapq
import time
import traceback
from typing import Optional

import bittensor as bt
import numpy as np
from pydantic import BaseModel

from redteam_core.validator.models import MinerChallengeCommit


class MinerChallengeInfo(BaseModel):
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

    miner_uid: int
    miner_hotkey: str
    challenge_name: str
    latest_commit: Optional[MinerChallengeCommit] = None
    best_commit: Optional[MinerChallengeCommit] = None
    daily_scores: dict[str, float] = {}

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

    def public_view(self) -> "MinerChallengeInfo":
        """Returns a new instance with sensitive fields removed from commits."""
        return MinerChallengeInfo(
            miner_uid=self.miner_uid,
            miner_hotkey=self.miner_hotkey,
            challenge_name=self.challenge_name,
            latest_commit=(
                self.latest_commit.public_view() if self.latest_commit else None
            ),
            best_commit=self.best_commit.public_view() if self.best_commit else None,
            daily_scores=self.daily_scores,
        )


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
        self.max_unique_commits = challenge_info["comparison_config"][
            "max_unique_commits"
        ]
        self._unique_commits_heap: list[tuple[float, str, str]] = (
            []
        )  # [(score, encrypted_commit, docker_hub_id)]
        self._unique_commits_set: set[str] = (
            set()
        )  # For O(1) lookup of existing commits

        # Track docker_hub_ids that have been successfully scored to avoid redundant commits
        self._unique_scored_docker_hub_ids: set[str] = set()

        # Miner states, mapping from uid to miner state
        self.miner_states: dict[int, MinerChallengeInfo] = {}

    def update_miner_infos(
        self, miner_commits: list[MinerChallengeCommit]
    ) -> list[MinerChallengeCommit]:
        """
        Update miner infos based on new commits.
        If an UID 's hotkey changes, a new miner info will be created.

        Args:
            miner_commits (dict): Dictionary of miner revealed commits with UID and SS58 address as keys.

        Returns:
            list[MinerChallengeCommit]: A list of miner commits that are updated for the challenge.
        """
        for miner_commit in miner_commits:
            current_miner_state: MinerChallengeInfo = self.miner_states.setdefault(
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
            and (
                miner_uid < len(self.metagraph.hotkeys)
                and self.metagraph.hotkeys[miner_uid] == miner_state.miner_hotkey
            )
        }

    def update_miner_scores(self, miner_commits: list[MinerChallengeCommit]):
        """
        Update miners 's latest submission scores and penalties.

        Args:
            miner_commits (list[MinerChallengeCommit]): List of miner commit objects
        """
        for miner_commit in miner_commits:
            if miner_commit.docker_hub_id in self._unique_scored_docker_hub_ids:
                # Skip if docker_hub_id has been scored
                continue

            if not miner_commit.scoring_logs:
                # Skip if no scoring logs
                continue

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
                        np.nanmax([log.similarity_score for log in logs] or [0.0])
                        for logs in miner_commit.comparison_logs.values()
                    ]
                    penalty = np.max(penalty_values).item() if penalty_values else 0
                    if np.isnan(penalty):
                        miner_commit.penalty = 0.0
                    else:
                        miner_commit.penalty = float(penalty)
                else:
                    miner_commit.penalty = 0.0

            except Exception:
                bt.logging.error(
                    f"[CHALLENGE MANAGER] Challenge {self.challenge_name}, failed to get commit {miner_commit.encrypted_commit} scores and penalties: {traceback.format_exc()}"
                )
                continue

            miner_commit.accepted = miner_commit.penalty < self.challenge_info.get(
                "penalty_threshold", 0.5
            )

            if not miner_commit.accepted:
                continue

            miner_commit.scored_timestamp = time.time()

            # Update miner 's best submission if current score is higher
            miner_state = self.miner_states.get(miner_commit.miner_uid)
            miner_state.update_best_commit(miner_commit)

            # Try to add to unique solutions set if commit is accepted
            if miner_commit.accepted and miner_commit.encrypted_commit:
                bt.logging.info(
                    f"[CHALLENGE MANAGER] Adding miner commit `{miner_commit.miner_uid}` to unique commit set"
                )
                self._try_add_unique_commit(
                    encrypted_commit=miner_commit.encrypted_commit,
                    score=miner_commit.score,
                    docker_hub_id=miner_commit.docker_hub_id,
                )

            # Mark docker_hub_id as scored after successful scoring
            self._unique_scored_docker_hub_ids.add(miner_commit.docker_hub_id)

    def _try_add_unique_commit(
        self, encrypted_commit: str, score: float, docker_hub_id: str
    ):
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
            heapq.heappush(
                self._unique_commits_heap, (score, encrypted_commit, docker_hub_id)
            )
            self._unique_commits_set.add(encrypted_commit)
        elif score > self._unique_commits_heap[0][0]:
            # Score is better than our worst commit, replace it
            _, old_commit, _ = heapq.heapreplace(
                self._unique_commits_heap, (score, encrypted_commit, docker_hub_id)
            )
            self._unique_commits_set.remove(old_commit)
            self._unique_commits_set.add(encrypted_commit)

    def get_unique_commits(self) -> set[str]:
        return self._unique_commits_set

    def get_unique_scored_docker_hub_ids(self) -> set[str]:
        return self._unique_scored_docker_hub_ids

    def get_challenge_scores(self):
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        scores = np.zeros(len(uids))

        for _, miner_state in self.miner_states.items():
            if (
                miner_state.miner_uid in uids
                and miner_state.miner_hotkey in self.metagraph.hotkeys
                and miner_state.miner_hotkey
                == self.metagraph.hotkeys[miner_state.miner_uid]
                and miner_state.best_commit is not None
            ):
                scores[miner_state.miner_uid] = miner_state.best_commit.score

        # Apply softmax
        temperature = self.challenge_info.get("temperature", 0.2)
        scaled_scores = scores / temperature
        scores_exp = np.exp(scaled_scores - np.max(scaled_scores))
        softmax_scores = scores_exp / np.sum(scores_exp)

        return softmax_scores

    def export_state(self, public_view: bool = False) -> dict:
        """
        Exports the current state of the ChallengeManager to a serializable dictionary.
        Only exports dynamic state that needs to be preserved between sessions.

        Returns:
            dict: A dictionary containing the serialized state
        """
        state = {
            "unique_commits": [
                {
                    "score": float(score),
                    "commit": commit,
                    "docker_hub_id": docker_hub_id,
                }  # Convert tuple to dict for explicit serialization
                for score, commit, docker_hub_id in self._unique_commits_heap
            ],
            "unique_scored_docker_hub_ids": list(self._unique_scored_docker_hub_ids),
            "miner_states": {
                str(uid): (
                    miner_state.public_view().model_dump()
                    if public_view
                    else miner_state.model_dump()
                )
                for uid, miner_state in self.miner_states.items()
            },
        }

        return state

    @classmethod
    def load_state(
        cls, state: dict, challenge_info: dict, metagraph: bt.metagraph
    ) -> "ChallengeManager":
        """
        Creates a new ChallengeManager instance from a serialized state.

        Args:
            state (dict): The serialized state dictionary
            challenge_info (dict): The challenge configuration info
            metagraph (bt.metagraph): The Bittensor metagraph

        Returns:
            ChallengeManager: A new instance with the loaded state
        """
        instance = cls(challenge_info, metagraph)

        # Restore unique commits
        instance._unique_commits_heap = [
            (
                item["score"],
                item["commit"],
                item["docker_hub_id"],
            )  # Convert back to tuple
            for item in state["unique_commits"]
        ]
        # Reconstruct set from heap
        instance._unique_commits_set = {
            commit for _, commit, _ in instance._unique_commits_heap
        }
        # Load scored docker hub IDs
        instance._unique_scored_docker_hub_ids = set(
            state.get("unique_scored_docker_hub_ids", [])
        )

        # Restore miner states using Pydantic's model_validate
        instance.miner_states = {
            int(uid): MinerChallengeInfo.model_validate(miner_state_data)
            for uid, miner_state_data in state["miner_states"].items()
        }

        return instance

    def _validate_miner_in_metagraph(self, miner_uid: int, miner_hotkey: str) -> bool:
        return (
            miner_uid < len(self.metagraph.hotkeys)
            and self.metagraph.hotkeys[miner_uid] == miner_hotkey
        )
