import datetime
import time
import traceback
from copy import deepcopy
from typing import Optional

import bittensor as bt
import numpy as np
from cryptography.fernet import Fernet

from redteam_core import BaseValidator, Commit, challenge_pool, constants
from redteam_core.validator import (
    ChallengeManager,
    ScoringLog,
    start_bittensor_log_listener,
)
from redteam_core.validator.miner_manager import MinerManager
from redteam_core.validator.models import MinerChallengeCommit
from redteam_core.validator.utils import create_validator_request_header_fn

class Validator(BaseValidator):
    def __init__(self, config: bt.Config):
        """
        Initializes the Validator without requiring external storage.
        """
        super().__init__(config)

        self.validator_request_header_fn = create_validator_request_header_fn(
            self.uid, self.wallet.hotkey.ss58_address, self.wallet.hotkey
        )

        # Try to start log listener but skip if storage is unavailable
        try:
            storage_api_key = "test"  # Dummy value
            start_bittensor_log_listener(api_key=storage_api_key)
        except Exception as e:
            bt.logging.warning(f"[INIT] Skipping log listener: {e}")

        self.challenge_managers: dict[str, ChallengeManager] = {}
        self.miner_managers: MinerManager = MinerManager(
            metagraph=self.metagraph, challenge_managers=self.challenge_managers
        )
        self._init_active_challenges()

        self.miner_commits = {}  # Keep in-memory miner commits
        self.scoring_dates: list[str] = []

    def _init_active_challenges(self):
        """
        Initializes active challenges.
        """
        all_challenges = deepcopy(challenge_pool.ACTIVE_CHALLENGES)
        self.active_challenges = all_challenges

        for challenge in self.active_challenges.keys():
            if challenge not in self.challenge_managers:
                self.challenge_managers[challenge] = ChallengeManager(
                    challenge_info=self.active_challenges[challenge],
                    metagraph=self.metagraph,
                )

        self.miner_managers.update_challenge_managers(self.challenge_managers)

    def forward(self):
        """
        Execute the main validation cycle for all active challenges.
        """
        self._init_active_challenges()
        self.update_miner_commits(self.active_challenges)
        bt.logging.success(f"[FORWARD] Forwarding at {datetime.datetime.now(datetime.timezone.utc)}")
        revealed_commits = self.get_revealed_commits()

        for challenge, challenge_manager in self.challenge_managers.items():
            if challenge not in revealed_commits:
                continue
            updated_miner_commits = challenge_manager.update_miner_infos(
                miner_commits=revealed_commits.get(challenge, [])
            )
            revealed_commits[challenge] = updated_miner_commits

        self.forward_local_scoring(revealed_commits)

    def forward_local_scoring(self, revealed_commits: dict[str, list[MinerChallengeCommit]]):
        """
        Execute local scoring for revealed miner commits.
        """
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if today in self.scoring_dates:
            bt.logging.warning(f"[FORWARD LOCAL SCORING] Skipping scoring for {today}")
            return

        bt.logging.info(f"[FORWARD LOCAL SCORING] Running scoring for {today}")
        for challenge, commits in revealed_commits.items():
            if challenge not in self.active_challenges:
                continue
            self.challenge_managers[challenge].update_miner_scores(commits)

        self.scoring_dates.append(today)
        bt.logging.success(f"[FORWARD LOCAL SCORING] Scoring completed for {today}")

    def update_miner_commits(self, active_challenges: dict):
        """
        Queries the axons for miner commit updates and decrypts them if necessary.
        """
        uids = self.metagraph.uids
        axons = [self.metagraph.axons[i] for i in uids]
        ss58_addresses = [self.metagraph.hotkeys[i] for i in uids]
        dendrite = bt.dendrite(wallet=self.wallet)
        synapse = Commit()
        responses = dendrite.query(axons, synapse, timeout=constants.QUERY_TIMEOUT)

        for uid, ss58_address, response in zip(uids, ss58_addresses, responses):
            this_miner_commit = self.miner_commits.setdefault((uid, ss58_address), {})
            encrypted_commit_dockers = response.encrypted_commit_dockers
            keys = response.public_keys

            for challenge_name, encrypted_commit in encrypted_commit_dockers.items():
                if challenge_name not in active_challenges:
                    this_miner_commit.pop(challenge_name, None)
                    continue

                current_miner_commit = this_miner_commit.setdefault(
                    challenge_name,
                    MinerChallengeCommit(
                        miner_uid=uid,
                        miner_ss58_address=ss58_address,
                        challenge_name=challenge_name,
                    ),
                )

                if encrypted_commit != current_miner_commit.encrypted_commit:
                    current_miner_commit.commit_timestamp = time.time()
                    current_miner_commit.encrypted_commit = encrypted_commit
                    current_miner_commit.key = keys.get(challenge_name)
                    current_miner_commit.commit = ""

                if keys.get(challenge_name):
                    current_miner_commit.key = keys.get(challenge_name)

                if current_miner_commit.key:
                    try:
                        f = Fernet(current_miner_commit.key)
                        commit = f.decrypt(current_miner_commit.encrypted_commit).decode()
                        current_miner_commit.commit = commit
                    except Exception as e:
                        bt.logging.error(f"Failed to decrypt commit: {e}")

    def get_revealed_commits(self) -> dict[str, list[MinerChallengeCommit]]:
        """
        Collects all revealed commits from miners.
        """
        revealed_commits = {}
        for (uid, ss58_address), commits in self.miner_commits.items():
            for challenge_name, commit in commits.items():
                if commit.commit:
                    revealed_commits.setdefault(challenge_name, []).append(commit)
        return revealed_commits

if __name__ == "__main__":
    with Validator(get_config()) as validator:
        while True:
            bt.logging.info("Validator is running...")
            validator.forward()
            time.sleep(constants.EPOCH_LENGTH // 4)