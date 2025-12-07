from abc import abstractmethod
import heapq

import bittensor as bt

from redteam_core.validator.models import MinerChallengeCommit, MinerChallengeInfo


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

    @abstractmethod
    def update_miner_scores(self, miner_commits: list[MinerChallengeCommit]):
        """Update miners 's latest submission scores and penalties."""

    @abstractmethod
    def get_challenge_scores(self):
        pass
