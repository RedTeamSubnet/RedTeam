#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import traceback
from copy import deepcopy

import bittensor as bt
import numpy as np
import requests
from cryptography.fernet import Fernet

from redteam_core import BaseValidator, Commit, challenge_pool, constants
from redteam_core.common import get_config
from redteam_core.validator import (
    ChallengeManager,
    StorageManager,
    start_bittensor_log_listener,
)
from redteam_core.validator.miner_manager import MinerManager
from redteam_core.validator.models import (
    MinerChallengeCommit,
    ComparisonLog,
    ScoringLog,
)
from redteam_core.validator.utils import create_validator_request_header_fn


class Validator(BaseValidator):
    def __init__(self, config: bt.Config):
        """
        A validator node that manages challenge scoring and miner evaluation in the network.

        Core Responsibilities:
        - Manages active challenges and their scoring processes
        - Collects and verifies encrypted miner submissions
        - Executes scoring either locally or via centralized server
        - Maintains validator state and scoring history
        - Updates on-chain weights based on miner performance

        Key Components:
        - storage_manager: Handles persistent storage
        - challenge_managers: Per-challenge scoring logic
        - miner_managers: Tracks miner performance
        - miner_commits: {(uid, hotkey): {challenge_name: MinerCommit}}
        - scoring_dates: Record of completed scoring dates

        Note:
        Scoring occurs daily at a configured hour, with support for both
        local and centralized scoring modes.
        """
        super().__init__(config)

        self.validator_request_header_fn = create_validator_request_header_fn(
            validator_uid=self.uid,
            validator_hotkey=self.wallet.hotkey.ss58_address,
            keypair=self.wallet.hotkey,
        )

        # Get the storage API key
        storage_api_key = self._get_storage_api_key()

        # Start the Bittensor log listener
        start_bittensor_log_listener(api_key=storage_api_key)

        # Setup storage manager and publish public hf_repo_id for storage
        self.storage_manager = StorageManager(
            cache_dir=self.config.validator.cache_dir,
            validator_request_header_fn=self.validator_request_header_fn,
            hf_repo_id=self.config.validator.hf_repo_id,
            sync_on_init=True,
        )
        # Commit the repo_id
        self.commit_repo_id_to_chain(
            hf_repo_id=self.config.validator.hf_repo_id, max_retries=5
        )

        self.challenge_managers: dict[str, ChallengeManager] = {}
        self.miner_managers: MinerManager = MinerManager(
            metagraph=self.metagraph,
            challenge_managers=self.challenge_managers,
        )
        self._init_active_challenges()

        # Initialize validator state
        self.miner_commits: dict[
            tuple[int, str], dict[str, MinerChallengeCommit]
        ] = {}  # {(uid, hotkey): {challenge_name: MinerCommit}}
        self.scoring_dates: list[str] = []
        self._init_validator_state()

    # MARK: Initialization and Setup
    def _init_active_challenges(self):
        """
        Initializes and updates challenge managers based on current active challenges.
        Filters challenges by date and maintains challenge manager consistency.
        """
        # Avoid mutating the original ACTIVE_CHALLENGES
        all_challenges = deepcopy(challenge_pool.ACTIVE_CHALLENGES)

        # Remove challenges that are not active and setup the active challenges
        if datetime.datetime.now(datetime.timezone.utc) <= datetime.datetime(
            2025, 4, 23, 14, 0, 0, 0, datetime.timezone.utc
        ):
            all_challenges.pop("humanize_behaviour_v3", None)
        else:
            all_challenges.pop("humanize_behaviour_v2", None)

        self.active_challenges = all_challenges

        # Add challenge managers for all active challenges
        for challenge in self.active_challenges.keys():
            if challenge not in self.challenge_managers:
                self.challenge_managers[challenge] = self.active_challenges[challenge][
                    "challenge_manager"
                ](
                    challenge_info=self.active_challenges[challenge],
                    metagraph=self.metagraph,
                )

        # Remove challenge managers for inactive challenges with dict comprehension
        self.challenge_managers = {
            challenge: self.challenge_managers[challenge]
            for challenge in self.challenge_managers
            if challenge in self.active_challenges
        }

        self.miner_managers.update_challenge_managers(self.challenge_managers)

    def _init_validator_state(self):
        """
        Initialize validator state by loading from storage/cache.
        Uses centralized storage when centralized scoring is enabled,
        otherwise uses local cache.

        If no state is found, keeps the default empty state.
        """
        bt.logging.info("[INIT] Starting validator state initialization...")

        state = None

        # Try to load state based on scoring configuration
        if self.config.validator.use_centralized_scoring:
            # Try to get state from centralized storage
            bt.logging.info(
                f"[INIT] Trying to get validator state from centralized storage for validator {self.uid}, hotkey: {self.wallet.hotkey.ss58_address}"
            )
            state = self.storage_manager.get_latest_validator_state_from_storage(
                validator_uid=self.uid,
                validator_hotkey=self.wallet.hotkey.ss58_address,
            )
            if not state:
                bt.logging.warning(
                    f"[INIT] No validator state found in centralized storage for validator {self.uid}, hotkey: {self.wallet.hotkey.ss58_address}, falling back to cache"
                )
                state = self.storage_manager.get_latest_validator_state_from_cache(
                    validator_uid=self.uid,
                    validator_hotkey=self.wallet.hotkey.ss58_address,
                )
            else:
                bt.logging.success(
                    f"[INIT] Successfully retrieved validator state from centralized storage for validator {self.uid}, hotkey: {self.wallet.hotkey.ss58_address}"
                )
        else:
            bt.logging.info(
                f"[INIT] Trying to get validator state from local cache for validator {self.uid}, hotkey: {self.wallet.hotkey.ss58_address}"
            )
            state = self.storage_manager.get_latest_validator_state_from_cache(
                validator_uid=self.uid,
                validator_hotkey=self.wallet.hotkey.ss58_address,
            )

        if state:
            # Load the state into the current instance
            self.load_state(state)
            bt.logging.success("[INIT] Successfully loaded existing validator state")
        else:
            bt.logging.info("[INIT] No existing state found, using empty state")

        bt.logging.success("[INIT] Validator state initialization completed")

    # MARK: Validation Loop
    def forward(self):
        """
        Execute the main validation cycle for all active challenges.

        Flow:
            - Query miners → Reveal commits → Score → Store

        The scoring method is determined by the config setting 'use_centralized_scoring':
            - True: Uses centralized scoring server
            - False: Runs scoring locally on validator 's machine

        Note: This method is called periodically as part of the validator's
        main loop to process new miner commits and update scores.
        """
        date_time = datetime.datetime.now(datetime.timezone.utc)
        bt.logging.info(f"[FORWARD] Forwarding for {date_time}")
        self._init_active_challenges()
        bt.logging.success(
            f"[FORWARD] Active challenges initialized for {date_time}: {self.active_challenges}"
        )

        self.update_miner_commits(self.active_challenges)
        bt.logging.success(f"[FORWARD] Miner commits updated for {date_time}")

        revealed_commits = self.get_revealed_commits()
        bt.logging.success(f"[FORWARD] Revealed commits updated for {date_time}")

        # Update miner infos
        for challenge, challenge_manager in self.challenge_managers.items():
            if challenge not in revealed_commits:
                continue
            challenge_manager.update_miner_infos(
                miner_commits=revealed_commits.get(challenge, [])
            )

        # Forward the revealed commits to the appropriate scoring method
        if self.config.validator.use_centralized_scoring:
            self.forward_centralized_scoring(revealed_commits)
        else:
            self.forward_local_scoring(revealed_commits)

        # Store results
        self._store_miner_commits()
        self._store_validator_state()

    def forward_centralized_scoring(
        self, revealed_commits: dict[str, list[MinerChallengeCommit]]
    ):
        """
        Forward pass for centralized scoring.
        1. Save revealed commits to storage
        2. Get scored commits from centralized scoring endpoint
        3. Update scores if scoring for all submissions of a challenge is done

        Args:
            revealed_commits (dict[str, list[MinerChallengeCommit]]): Mapping of challenge names to the revealed miner commits
                Format: {
                    "challenge_name": [MinerChallengeCommit]
                }
        """
        bt.logging.info(
            "[FORWARD CENTRALIZED SCORING] Saving Revealed commits to storage ..."
        )
        # Extra storing to make sure centralized scoring server has the latest miner commits
        self._store_miner_commits()

        # Get current time info
        today = datetime.datetime.now(datetime.timezone.utc)
        today_key = today.strftime("%Y-%m-%d")
        current_hour = today.hour
        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates
        # Validate if scoring is due
        if validate_scoring_hour and validate_scoring_date and revealed_commits:
            # Initialize a dictionary to track if scoring is done for each challenge
            is_scoring_done = {
                challenge_name: False for challenge_name in revealed_commits.keys()
            }

            # Loop until all challenges have finished scoring
            while True:
                for challenge, commits in revealed_commits.items():
                    # Skip if challenge is not active
                    if challenge not in self.active_challenges:
                        continue

                    # Skip if there are no commits for the challenge
                    if not commits:
                        bt.logging.info(
                            f"[FORWARD CENTRALIZED SCORING] No commits for challenge: {challenge}"
                        )
                        is_scoring_done[challenge] = True
                        continue

                    # Skip if scoring is already done for the challenge
                    if is_scoring_done[challenge]:
                        continue

                    try:
                        bt.logging.info(
                            f"[FORWARD CENTRALIZED SCORING] Getting scored commits from centralized scoring endpoint for challenge: {challenge} ..."
                        )
                        commits, is_done = self.get_centralized_scoring_results(
                            challenge, commits
                        )
                        is_scoring_done[challenge] = is_done

                        if is_done:
                            bt.logging.info(
                                f"[FORWARD CENTRALIZED SCORING] Scoring for challenge: {challenge} has been completed for {today_key}"
                            )
                            self.challenge_managers[challenge].update_miner_scores(
                                commits
                            )
                        else:
                            bt.logging.warning(
                                f"[FORWARD CENTRALIZED SCORING] Scoring for challenge: {challenge} is not done yet"
                            )
                    except Exception:
                        # Continue to next challenge if error occurs
                        bt.logging.error(
                            f"[FORWARD CENTRALIZED SCORING] Error getting scored commits and update scores for challenge: {challenge}: {traceback.format_exc()}"
                        )
                        continue

                # Break if all challenges have finished scoring
                if all(is_scoring_done.values()):
                    break
                # Sleep for a period before checking again
                time.sleep(60 * 10)

            bt.logging.info(
                f"[FORWARD CENTRALIZED SCORING] All tasks: Scoring completed for {today_key}"
            )
            self.scoring_dates.append(today_key)
        else:
            bt.logging.warning(
                f"[FORWARD CENTRALIZED SCORING] Skipping scoring for {today_key}"
            )
            bt.logging.info(
                f"[FORWARD CENTRALIZED SCORING] Current hour: {current_hour}, Scoring hour: {constants.SCORING_HOUR}"
            )
            bt.logging.info(
                f"[FORWARD CENTRALIZED SCORING] Scoring dates: {self.scoring_dates}"
            )
            bt.logging.info(
                f"[FORWARD CENTRALIZED SCORING] Revealed commits: {str(revealed_commits)[:100]}..."
            )

    def forward_local_scoring(
        self, revealed_commits: dict[str, list[MinerChallengeCommit]]
    ):
        """
        Execute local scoring for revealed miner commits.

        This method handles the local scoring workflow:
        1. Validates if scoring should be performed based on time conditions
        2. For each eligible challenge:
            - Check challenge manager and storage manager for comparison inputs
            - Runs the challenge controller on miner's submission with new inputs generated for scoring and comparison
            - Compare miner's output with the unique solutions set
            - Updates scores in challenge manager
        3. Updates all scoring logs after validating

        Args:
            revealed_commits (dict[str, list[MinerChallengeCommit]]): Mapping of challenge names to the revealed miner commits
                Format: {
                    "challenge_name": [MinerChallengeCommit]
                }

        Time Conditions:
            - Current hour must be >= SCORING_HOUR
            - Today's date must not be in scoring_dates
            - There must be revealed commits to score
        """
        # Get current time info
        today = datetime.datetime.now(datetime.timezone.utc)
        current_hour = today.hour
        today_key = today.strftime("%Y-%m-%d")
        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates

        # Validate if scoring is due
        if validate_scoring_hour and validate_scoring_date and revealed_commits:
            bt.logging.info(f"[FORWARD LOCAL SCORING] Running scoring for {today_key}")

            for challenge, commits in revealed_commits.items():
                if challenge not in self.active_challenges:
                    continue
                if not commits:
                    bt.logging.info(
                        f"[FORWARD LOCAL SCORING] No commits for challenge: {challenge}"
                    )
                    continue

                bt.logging.info(
                    f"[FORWARD LOCAL SCORING] Running controller for challenge: {challenge}"
                )
                # 1. Gather comparison inputs
                # Get unique commits for the challenge (the "encrypted_commit"s)
                unique_commits = self.challenge_managers[challenge].get_unique_commits()
                # Get unique solutions 's cache key
                unique_commits_cache_keys = [
                    self.storage_manager.hash_cache_key(unique_commit)
                    for unique_commit in unique_commits
                ]
                # Get commit 's cached data from storage
                unique_commits_cached_data: list[MinerChallengeCommit] = []
                challenge_local_cache = self.storage_manager._get_cache(challenge)
                if challenge_local_cache:
                    unique_commits_cached_data_raw = [
                        challenge_local_cache.get(unique_commit_cache_key)
                        for unique_commit_cache_key in unique_commits_cache_keys
                    ]

                    unique_commits_cached_data = []
                    for commit in unique_commits_cached_data_raw:
                        if not commit:
                            continue
                        try:
                            validated_commit = MinerChallengeCommit.model_validate(
                                commit
                            )
                            unique_commits_cached_data.append(validated_commit)
                        except Exception:
                            bt.logging.warning(
                                f"[FORWARD LOCAL SCORING] Failed to validate cached commit {commit} for challenge {challenge}: {traceback.format_exc()}"
                            )
                            continue

                # 2. Run challenge controller
                bt.logging.info(
                    f"[FORWARD LOCAL SCORING] Running controller for challenge: {challenge}"
                )
                controller = self.active_challenges[challenge]["controller"](
                    challenge_name=challenge,
                    miner_commits=commits,
                    reference_comparison_commits=unique_commits_cached_data,
                    challenge_info=self.active_challenges[challenge],
                )
                # Run challenge controller, the controller update commit 's scoring logs and reference comparison logs directly
                controller.start_challenge()

                # 3. Run comparer
                bt.logging.info(
                    f"[FORWARD LOCAL SCORING] Running comparer for challenge: {challenge}"
                )
                comparer = self.active_challenges[challenge]["comparer"](
                    challenge_name=challenge,
                    challenge_info=self.active_challenges[challenge],
                    miner_commits=commits,
                    compare_with_each_other=True,
                )
                # Run comparison, the comparer update commit 's penalty and comparison logs directly
                comparer.start_comparison()

                # 4. Update scores and penalties to challenge manager
                self.challenge_managers[challenge].update_miner_scores(commits)
                bt.logging.info(
                    f"[FORWARD LOCAL SCORING] Scoring for challenge: {challenge} has been completed for {today_key}"
                )

            bt.logging.info(
                f"[FORWARD LOCAL SCORING] All tasks: Scoring completed for {today_key}"
            )
            self.scoring_dates.append(today_key)
        else:
            bt.logging.warning(
                f"[FORWARD LOCAL SCORING] Skipping scoring for {today_key}"
            )
            bt.logging.info(
                f"[FORWARD LOCAL SCORING] Current hour: {current_hour}, Scoring hour: {constants.SCORING_HOUR}"
            )
            bt.logging.info(
                f"[FORWARD LOCAL SCORING] Scoring dates: {self.scoring_dates}"
            )
            bt.logging.info(
                f"[FORWARD LOCAL SCORING] Revealed commits: {str(revealed_commits)[:100]}..."
            )

    def get_centralized_scoring_results(
        self,
        challenge_name: str,
        revealed_commits: list[MinerChallengeCommit],
    ) -> tuple[list[MinerChallengeCommit], bool]:
        """
        Get scored commits from centralized server and determine if scoring is complete for all revealed commits in challenge.

        Args:
            challenge_name: Name of the challenge
            revealed_commits: List of MinerChallengeCommit objects

        Returns:
            tuple: (scored_commits, is_scoring_done)
                - scored_commits: List of MinerChallengeCommit objects
                - is_scoring_done: True if all revealed commits have scores, this will be determined by the server.
        """
        try:
            if not revealed_commits:
                return [], True

            # Extract encrypted commits
            encrypted_commits = [commit.encrypted_commit for commit in revealed_commits]

            # Query centralized scoring server
            endpoint = f"{constants.REWARDING_URL}/get_scoring_result"
            response = requests.post(
                endpoint,
                json={
                    "challenge_name": challenge_name,
                    "encrypted_commits": encrypted_commits,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            # Update commits with results
            scored_commits = []
            for commit in revealed_commits:
                if not commit.encrypted_commit:
                    continue

                result = data.get("commits", {}).get(commit.encrypted_commit)
                if result:
                    # Update commit with scoring results
                    commit.scoring_logs = [
                        ScoringLog.model_validate(scoring_log)
                        for scoring_log in result.get("scoring_logs", [])
                    ]
                    commit.comparison_logs = {
                        docker_hub_id: [
                            ComparisonLog.model_validate(comparison_log)
                            for comparison_log in _comparison_logs
                        ]
                        for docker_hub_id, _comparison_logs in result.get(
                            "comparison_logs", {}
                        ).items()
                    }
                    scored_commits.append(commit)

            return scored_commits, data.get("is_done", False)

        except Exception:
            bt.logging.error(
                f"Error getting centralized scoring results: {traceback.format_exc()}"
            )
            return [], False

    def set_weights(self) -> None:
        """
        Sets the weights of the miners on-chain based on their accumulated scores.
        Accumulates scores from all challenges.
        """
        n_uids = int(self.metagraph.n)
        uids = list(range(n_uids))
        weights = np.zeros(len(uids))

        scores = self.miner_managers.get_onchain_scores(n_uids)
        bt.logging.debug(f"[SET WEIGHTS] scores: {scores}")
        weights = scores
        (
            processed_weight_uids,
            processed_weights,
        ) = bt.utils.weight_utils.process_weights_for_netuid(
            uids=self.metagraph.uids,
            weights=weights,
            netuid=self.config.netuid,
            subtensor=self.subtensor,
            metagraph=self.metagraph,
        )
        (
            uint_uids,
            uint_weights,
        ) = bt.utils.weight_utils.convert_weights_and_uids_for_emit(
            uids=processed_weight_uids, weights=processed_weights
        )

        bt.logging.info(
            f"[SET WEIGHTS] uint_weights: {uint_weights}, processed_weights: {processed_weights}"
        )

        # Set weights on-chain
        result, log = self.subtensor.set_weights(
            wallet=self.wallet,
            netuid=self.config.netuid,
            uids=uint_uids,
            weights=uint_weights,
            version_key=constants.SPEC_VERSION,
        )

        if result:
            bt.logging.success(f"[SET WEIGHTS]: {log}")
        else:
            bt.logging.error(f"[SET WEIGHTS]: {log}")

    # MARK: Commit Management
    def update_miner_commits(self, active_challenges: dict):
        """
        Queries the axons for miner commit updates and decrypts them if the reveal interval has passed.
        """
        uids = [int(uid) for uid in self.metagraph.uids]

        axons = [self.metagraph.axons[i] for i in uids]
        hotkeys = [self.metagraph.hotkeys[i] for i in uids]
        dendrite = bt.dendrite(wallet=self.wallet)
        synapse = Commit()

        responses: list[Commit] = dendrite.query(
            axons, synapse, timeout=constants.QUERY_TIMEOUT
        )

        # Update new miner commits to self.miner_commits
        for uid, hotkey, response in zip(uids, hotkeys, responses):
            this_miner_commit = self.miner_commits.setdefault((uid, hotkey), {})
            encrypted_commit_dockers = response.encrypted_commit_dockers
            keys = response.public_keys

            # Update miner commits for each submitted challenge
            for challenge_name, encrypted_commit in encrypted_commit_dockers.items():
                if challenge_name not in active_challenges:
                    this_miner_commit.pop(challenge_name, None)
                    continue

                current_miner_challenge_commit = this_miner_commit.setdefault(
                    challenge_name,
                    MinerChallengeCommit(
                        miner_uid=uid,
                        miner_hotkey=hotkey,
                        challenge_name=challenge_name,
                    ),
                )
                # Update miner commit data if it's new
                if encrypted_commit != current_miner_challenge_commit.encrypted_commit:
                    # Create a completely new commit object for new submissions
                    new_commit = MinerChallengeCommit(
                        miner_uid=uid,
                        miner_hotkey=hotkey,
                        challenge_name=challenge_name,
                        commit_timestamp=time.time(),
                        encrypted_commit=encrypted_commit,
                        key=keys.get(challenge_name),
                    )
                    # Update miner commit
                    this_miner_commit[challenge_name] = current_miner_challenge_commit = (
                        new_commit
                    )
                elif keys.get(challenge_name):
                    current_miner_challenge_commit.key = keys.get(challenge_name)

                # Reveal commit if the interval has passed
                commit_timestamp = current_miner_challenge_commit.commit_timestamp
                encrypted_commit = current_miner_challenge_commit.encrypted_commit
                key = current_miner_challenge_commit.key
                if key and constants.is_commit_on_time(commit_timestamp):
                    try:
                        f = Fernet(key)
                        commit = f.decrypt(encrypted_commit).decode()
                        current_miner_challenge_commit.commit = commit
                        bt.logging.success(
                            f"Decrypted commit: {uid} - {hotkey} - {challenge_name} - {current_miner_challenge_commit.encrypted_commit} to {current_miner_challenge_commit.commit}"
                        )
                    except Exception as e:
                        bt.logging.error(f"Failed to decrypt commit: {e}")

            # Filter out commits that are not in active challenges
            challenge_names_to_remove = [
                challenge_name
                for challenge_name in this_miner_commit.keys()
                if challenge_name not in active_challenges
            ]
            for challenge_name in challenge_names_to_remove:
                this_miner_commit.pop(challenge_name, None)

        # Cutoff miners not in metagraph using dict comprehension
        self.miner_commits = {
            (uid, hotkey): commits
            for (uid, hotkey), commits in self.miner_commits.items()
            if hotkey in self.metagraph.hotkeys
        }

        # Sort by UID to make sure all next operations are order consistent
        self.miner_commits = {
            (uid, hotkey): commits
            for (uid, hotkey), commits in sorted(
                self.miner_commits.items(), key=lambda item: item[0]
            )
        }

    def get_revealed_commits(self) -> dict[str, list[MinerChallengeCommit]]:
        """
        Collects all revealed commits from miners.
        Filters unique docker_hub_ids in one pass and excludes previously scored submissions.

        Returns:
            A dictionary where the key is the challenge name and the value is a list of MinerChallengeCommit.
        """
        seen_docker_hub_ids: set[str] = set()

        revealed_commits: dict[str, list[MinerChallengeCommit]] = {}
        for (uid, hotkey), commits in self.miner_commits.items():
            for challenge_name, commit in commits.items():
                bt.logging.info(
                    f"[GET REVEALED COMMITS] Try to reveal commit: {uid} - {hotkey} - {challenge_name} - {commit.encrypted_commit}"
                )
                if commit.commit:
                    this_challenge_revealed_commits = revealed_commits.setdefault(
                        challenge_name, []
                    )
                    docker_hub_id = commit.commit.split("---")[1]

                    if (
                        docker_hub_id in seen_docker_hub_ids
                        or docker_hub_id
                        in self.challenge_managers[
                            challenge_name
                        ].get_unique_scored_docker_hub_ids()
                    ):
                        # Only reveal unique docker hub ids in one pass, also ignore if docker_hub_id has been scored
                        continue
                    else:
                        commit.docker_hub_id = docker_hub_id
                        this_challenge_revealed_commits.append(commit)
                        seen_docker_hub_ids.add(docker_hub_id)
                        bt.logging.info(
                            f"[GET REVEALED COMMITS] Revealed commit: {uid} - {hotkey} - {challenge_name} - {commit.encrypted_commit}"
                        )

        return revealed_commits

    # MARK: Storage
    def _store_miner_commits(
        self, miner_commits: dict[str, list[MinerChallengeCommit]] = {}
    ):
        """
        Store miner commits to storage.
        """
        if not miner_commits:
            # Default to store all miner commits
            for _, miner_challenge_commits in self.miner_commits.items():
                for challenge_name, commit in miner_challenge_commits.items():
                    miner_commits.setdefault(challenge_name, []).append(commit)

        data_to_store: list[MinerChallengeCommit] = [
            commit
            for challenge_name, commits in miner_commits.items()
            for commit in commits
        ]

        try:
            self.storage_manager.update_commit_batch(
                commits=data_to_store, async_update=True
            )
        except Exception as e:
            bt.logging.error(f"Failed to queue miner commit data for storage: {e}")

    def _store_validator_state(self):
        """
        Store validator state to storage.
        """
        self.storage_manager.update_validator_state(
            data=self.export_state(), async_update=True
        )

    def commit_repo_id_to_chain(self, hf_repo_id: str, max_retries: int = 5) -> None:
        """
        Commits the repository ID to the blockchain, ensuring the process succeeds with retries.
        Also stores repo id to the centralized storage.

        Args:
            repo_id (str): The repository ID to commit.
            max_retries (int): Maximum number of retries in case of failure. Defaults to 5.

        Raises:
            RuntimeError: If the commitment fails after all retries.
        """
        message = f"{self.wallet.hotkey.ss58_address}---{hf_repo_id}"

        for attempt in range(1, max_retries + 1):
            try:
                bt.logging.info(
                    f"Attempting to commit repo ID '{hf_repo_id}' to the blockchain (Attempt {attempt})..."
                )
                self.subtensor.commit(
                    wallet=self.wallet,
                    netuid=self.config.netuid,
                    data=message,
                )
                bt.logging.success(
                    f"Successfully committed repo ID '{hf_repo_id}' to the blockchain."
                )
                return
            except Exception as e:
                bt.logging.error(
                    f"Error committing repo ID '{hf_repo_id}' on attempt {attempt}: {e}"
                )
                if attempt == max_retries:
                    bt.logging.error(
                        f"Failed to commit repo ID '{hf_repo_id}' to the blockchain after {max_retries} attempts."
                    )

    def _get_storage_api_key(self) -> str:
        """
        Retrieves the storage API key from the config.
        """
        endpoint = f"{constants.STORAGE_URL}/get-api-key"
        data = {
            "validator_uid": self.uid,
            "validator_hotkey": self.metagraph.hotkeys[self.uid],
        }
        header = self.validator_request_header_fn(data)
        response = requests.post(endpoint, json=data, headers=header)
        response.raise_for_status()
        return response.json()["api_key"]

    def _commit_repo_id_to_chain_periodically(
        self, hf_repo_id: str, interval: int
    ) -> None:
        """
        Periodically commits the repository ID to the blockchain.

        Args:
            interval (int): Time interval in seconds between consecutive commits.
        """
        while True:
            try:
                self.commit_repo_id_to_chain(hf_repo_id=hf_repo_id)
                bt.logging.info(
                    "Periodic commit HF repo id to chain completed successfully."
                )
            except Exception as e:
                bt.logging.error(
                    f"Error in periodic commit for repo ID '{self.config.validator.hf_repo_id}': {e}"
                )
            time.sleep(interval)

    # MARK: State
    def export_state(self, public_view: bool = False) -> dict:
        """
        Exports the current state of the Validator to a serializable dictionary.
        Only exports dynamic state that needs to be preserved between sessions.

        Returns:
            dict: A dictionary containing the serialized state
        """
        # We no longer export miner commits since:
        # 1. They change quickly and is taking up lots space.
        # 2. They are already inside challenge_managers 's state, miner_state.latest_commit if updated successfully.

        # miner_commits: list[dict] = []
        # for (uid, ss58), commits in self.miner_commits.items():
        #     miner_commits.append(
        #         {
        #             "uid": uid,
        #             "ss58": ss58,
        #             "commits": {
        #                 challenge_name: commit.public_view().model_dump()
        #                 if public_view
        #                 else commit.model_dump()
        #                 for challenge_name, commit in commits.items()
        #             },
        #         }
        #     )

        challenge_managers: dict[str, dict] = {
            challenge_name: manager.export_state(public_view=public_view)
            for challenge_name, manager in self.challenge_managers.items()
        }

        state = {
            "validator_uid": self.uid,
            "validator_hotkey": self.wallet.hotkey.ss58_address,
            "challenge_managers": challenge_managers,
            "scoring_dates": self.scoring_dates,
        }
        return state

    def load_state(self, state: dict) -> None:
        """
        Loads state into the current Validator instance.
        This method modifies the existing instance.

        Args:
            state (dict): The serialized state dictionary
        """
        # Load scoring dates
        self.scoring_dates = state.get("scoring_dates", [])

        # Load miner commits (no longer load directly since we removed it from export_state)
        # self.miner_commits = {}
        # for miner_data in state.get("miner_commits", []):
        #     uid = miner_data["uid"]
        #     ss58 = miner_data["ss58"]
        #     self.miner_commits[(uid, ss58)] = {
        #         challenge_name: MinerChallengeCommit.model_validate(commit_data)
        #         for challenge_name, commit_data in miner_data["commits"].items()
        #     }

        # Load challenge managers state using their load_state class method
        for challenge_name, manager_state in state.get(
            "challenge_managers", {}
        ).items():
            if challenge_name in self.challenge_managers:
                # Create new challenge manager with loaded state
                loaded_manager = self.challenge_managers[challenge_name].load_state(
                    state=manager_state,
                    challenge_info=self.active_challenges[challenge_name],
                    metagraph=self.metagraph,
                )
                # Update the existing challenge manager with the loaded state
                self.challenge_managers[challenge_name] = loaded_manager

        # Try to load miner commits from challenge managers
        for challenge_name, manager in self.challenge_managers.items():
            for miner_state in manager.miner_states.values():
                if miner_state.latest_commit:
                    self.miner_commits.setdefault(
                        (miner_state.miner_uid, miner_state.miner_hotkey), {}
                    )[challenge_name] = miner_state.latest_commit


if __name__ == "__main__":
    with Validator(get_config()) as validator:
        while True:
            bt.logging.info("Validator is running...")
            time.sleep(constants.EPOCH_LENGTH // 4)
