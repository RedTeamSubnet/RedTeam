#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import os
import threading
import time
import traceback
from typing import Annotated

import bittensor as bt
import requests
import uvicorn
from fastapi import Body, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from neurons.validator.validator import Validator
from redteam_core import constants
from redteam_core.common import get_config
from redteam_core.validator.models import (
    ComparisonLog,
    MinerChallengeCommit,
    ScoringLog,
)
from cache import ScoringLRUCache

REWARD_APP_HOTKEY = os.getenv("REWARD_APP_HOTKEY")
REWARD_APP_UID = -1


def get_reward_app_config() -> bt.Config:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reward_app.port", type=int, default=47920)
    parser.add_argument("--reward_app.epoch_length", type=int, default=60)
    config = get_config(parser)
    return config


class RewardApp(Validator):
    """
    A special validator that focuses on centralized scoring for the network.
    This validator:
    1. Does not participate in querying miners or setting weights
    2. Maintains state like regular validators
    3. Scores miner commits retrieved from storage
    4. Provides API endpoints for direct access to scoring results
    """

    def __init__(self, config: bt.Config):
        """
        Initialize the reward app with validator capabilities.

        Args:
            config (bt.Config): Bittensor configuration object

        State Management:
            - validators_miner_commits: Stores current miner commits from all validators
            - miner_commits: Aggregated miner commits from all validators
            - miner_commits_cache: Quick lookup cache mapping challenge_name---encrypted_commit to commit
            - scoring_results: Cache for scored docker_hub_ids with their scoring and comparison logs
            - is_scoring_done: Tracks scoring completion status for each challenge
        """
        super().__init__(config)
        # Initialize validator state, stores current miner commits from all validators
        self.validators_miner_commits: dict[
            tuple[int, str], dict[tuple[int, str], dict[str, MinerChallengeCommit]]
        ] = {}
        # Daily miner commits will now be aggregated in self.miner_commits
        self.miner_commits: dict[tuple[int, str], dict[str, MinerChallengeCommit]] = {}
        # Quick lookup for miner commits by encrypted_commit, this has no new information, just a cache
        self.miner_commits_cache: dict[str, MinerChallengeCommit] = {}
        # Cache for scored docker_hub_ids, map from challenge_name to docker_hub_id to the coresponding "scoring_logs" and "comparison_logs"
        self.scoring_results = ScoringLRUCache(
            challenges=list(self.active_challenges.keys()), maxsize_per_challenge=256
        )
        # Initialize cache for scoring results
        self._initialize_scoring_cache()
        # Sync the cache from scoring results retrieved from storage upon initialization
        self._sync_scoring_results_from_storage_to_cache()

        # Initialize scoring completion flags
        # This is used to check if the scoring for a challenge is done
        # Set to False when new miner commits are retrieved and True when all miner commits are scored and compared at scoring hour
        self.is_scoring_done: dict[str, bool] = {
            challenge_name: False for challenge_name in self.active_challenges.keys()
        }

        # Initialize FastAPI app (May change this to use bt.axon in the future)
        self.app = FastAPI()
        self.app.add_api_route(
            "/get_scoring_result",
            self.get_scoring_result,
            methods=["POST"],
        )
        Instrumentator().instrument(self.app).expose(self.app)
        # Run FastAPI server in a separate thread
        self.server_thread = threading.Thread(
            target=uvicorn.run,
            kwargs={
                "app": self.app,
                "host": "0.0.0.0",
                "port": self.config.reward_app.port,
                "log_level": "debug",
            },
            daemon=True,  # Ensures the thread stops when the main process exits
        )
        self.server_thread.start()
        bt.logging.info(
            f"FastAPI server is running on port {self.config.reward_app.port}!"
        )

    def setup_bittensor_objects(self):
        bt.logging.info("Setting up Bittensor objects.")
        self.wallet = bt.wallet(config=self.config)
        bt.logging.info(f"Wallet: {self.wallet}")
        self.subtensor = bt.subtensor(config=self.config)
        bt.logging.info(f"Subtensor: {self.subtensor}")
        self.dendrite = bt.dendrite(wallet=self.wallet)
        bt.logging.info(f"Dendrite: {self.dendrite}")
        self.metagraph = self.subtensor.metagraph(self.config.netuid)
        bt.logging.info(f"Metagraph: {self.metagraph}")

        if REWARD_APP_HOTKEY != self.wallet.hotkey.ss58_address:
            bt.logging.error(
                f"Reward app hotkey {REWARD_APP_HOTKEY} does not match wallet hotkey {self.wallet.hotkey.ss58_address}"
            )
            exit()
        else:
            self.hotkey = REWARD_APP_HOTKEY
            self.uid = REWARD_APP_UID
            bt.logging.success(
                f"Reward app initialized with hotkey: {self.hotkey}, uid: {self.uid}"
            )

    # MARK: Validation Loop
    def forward(self):
        # 1. Update subnet commits state
        # Update commits from all validators
        self._update_validators_miner_commits()
        # Update (aggregate) miner commits
        self._update_miner_commits()
        # Get revealed commits
        revealed_commits = self.get_revealed_commits()

        # Update miner infos
        for challenge, challenge_manager in self.challenge_managers.items():
            if challenge not in revealed_commits:
                continue
            challenge_manager.update_miner_infos(
                miner_commits=revealed_commits.get(challenge, [])
            )

            # Flag the challenge as not done scoring if there are still unscored submissions
            if revealed_commits[challenge]:
                self.is_scoring_done[challenge] = False

        # 2. Score and compare miner commits for each challenge
        for challenge in revealed_commits:
            if revealed_commits[challenge]:
                # Score and compare new commits
                self._score_and_compare_new_miner_commits(
                    challenge=challenge,
                    revealed_commits_list=revealed_commits[challenge],
                )

                # Update cache
                for commit in revealed_commits[challenge]:
                    self.scoring_results.set(
                        challenge=challenge,
                        docker_hub_id=commit.docker_hub_id,
                        result={
                            "scoring_logs": commit.scoring_logs,
                            "comparison_logs": commit.comparison_logs,
                        },
                    )

                bt.logging.info(
                    f"[CENTRALIZED SCORING] Scoring for challenge: {challenge} has been completed"
                )

                # Store commits and scoring cache from this challenge
                self._store_miner_commits(
                    miner_commits={challenge: revealed_commits[challenge]}
                )
                self._store_centralized_scoring(challenge_name=challenge)

        # Store reward app state, this can be viewed by other validators, so we need to make it public view
        self.storage_manager.update_validator_state(
            data=self.export_state(public_view=True), async_update=True
        )

        # 3. Finalize validator's daily state
        # Get current time info
        today = datetime.datetime.now(datetime.timezone.utc)
        today_key = today.strftime("%Y-%m-%d")
        current_hour = today.hour

        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates

        if validate_scoring_hour and validate_scoring_date:
            # At this point, all commits should be scored and compared against previous unique commits already, we now need to compare new commits with each other
            for challenge in revealed_commits:
                if revealed_commits[challenge]:
                    self._compare_miner_commits(
                        challenge=challenge,
                        revealed_commits_list=revealed_commits[challenge],
                        compare_with_each_other=True,
                    )

            # Update scores and penalties to challenge manager and mark challenge as done
            for challenge in revealed_commits:
                self.challenge_managers[challenge].update_miner_scores(
                    miner_commits=revealed_commits[challenge]
                )
                self.is_scoring_done[challenge] = True

                # Store commits and scoring cache from this challenge
                self._store_miner_commits(
                    miner_commits={challenge: revealed_commits[challenge]}
                )
                self._store_centralized_scoring(challenge_name=challenge)

            self.scoring_dates.append(today_key)

            # Store reward app state, this can be viewed by other validators, so we need to make it public view
            self.storage_manager.update_validator_state(
                data=self.export_state(public_view=True), async_update=True
            )
        else:
            bt.logging.info(
                f"[CENTRALIZED FORWARD] Not time to finalize daily result. Hour: {current_hour}, Date: {today_key}"
            )

    def _score_and_compare_new_miner_commits(
        self, challenge: str, revealed_commits_list: list[MinerChallengeCommit]
    ):
        """
        Score and do comparison for new miner commits for a specific challenge.
        The default comparing behaviour is to compare new commits with previous unique commits only, not with each other since we don't have new commits for the whole day yet

        Args:
            challenge (str): Challenge name
            revealed_commits_list (list[MinerChallengeCommit]): List of new commits to score

        Process:
        1. Look up cached results for already scored commits, use cached results for already scored commits
        2. Gather unique commits from challenge manager for comparison
        3. Retrieve cached data for reference commits
        4. Run challenge controller with:
           - New commits to be scored
           - Reference commits for comparison

        """
        if challenge not in self.active_challenges:
            return

        bt.logging.info(
            f"[CENTRALIZED SCORING] Scoring miner commits for challenge: {challenge}"
        )

        if not revealed_commits_list:
            bt.logging.info(
                f"[CENTRALIZED SCORING] No commits for challenge: {challenge}, skipping"
            )
            return

        # 1. Look up cached results for already scored commits, use cached results for already scored commits
        # Also construct input seeds for new commits, this will be using input from commits that in the same revealed list for comparison
        # We do this since commits being in the same revealed list means that they will be scored in same day
        new_commits: list[MinerChallengeCommit] = []
        seed_inputs: list[dict] = []

        input_seed_hashes_set: set[str] = set()
        for commit in revealed_commits_list:
            if commit.docker_hub_id in self.scoring_results.get_all_for_challenge(
                challenge
            ):
                # Use results for already scored commits
                cached_result = self.scoring_results.get(
                    challenge=challenge, docker_hub_id=commit.docker_hub_id
                )
                commit.scoring_logs = cached_result["scoring_logs"]
                commit.comparison_logs = cached_result["comparison_logs"]

                # Add input seed hash to set
                for scoring_log in commit.scoring_logs:
                    if (
                        scoring_log.input_hash
                        and scoring_log.input_hash not in input_seed_hashes_set
                    ):
                        input_seed_hashes_set.add(scoring_log.input_hash)
                        seed_inputs.append(scoring_log.miner_input)
            else:
                new_commits.append(commit)

        if not new_commits:
            # No new commits to score, skip
            bt.logging.info(
                f"[CENTRALIZED SCORING] No new commits to score for challenge: {challenge}, skipping"
            )
            return
        else:
            bt.logging.info(
                f"[CENTRALIZED SCORING] {len(new_commits)} new commits to score for challenge: {challenge}"
            )

        bt.logging.info(
            f"[CENTRALIZED SCORING] Running controller for challenge: {challenge}"
        )

        # 2. Gather comparison inputs
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
                    validated_commit = MinerChallengeCommit.model_validate(commit)
                    unique_commits_cached_data.append(validated_commit)
                except Exception:
                    bt.logging.warning(
                        f"[CENTRALIZED SCORING] Failed to validate cached commit {commit} for challenge {challenge}: {traceback.format_exc()}"
                    )
                    continue

        # 3. Run challenge controller
        bt.logging.info(
            f"[CENTRALIZED SCORING] Running controller for challenge: {challenge}"
        )
        bt.logging.info(
            f"[CENTRALIZED SCORING] Going to score {len(new_commits)} commits for challenge: {challenge}"
        )
        # This challenge controll will run with new inputs and reference commit input
        # Reference commits are collected from yesterday, so if same docker_hub_id commited same day, they can share comparison_logs field, and of course, scoring_logs field
        # If same docker_hub_id commited different day, the later one expected to be ignored anyway
        controller = self.active_challenges[challenge]["controller"](
            challenge_name=challenge,
            miner_commits=new_commits,
            reference_comparison_commits=unique_commits_cached_data,
            challenge_info=self.active_challenges[challenge],
            seed_inputs=seed_inputs,
        )
        # Run challenge controller, the controller update commit 's scoring logs and reference comparison logs directly
        controller.start_challenge()

        # 4. Do comparison for new commits with each other, we only compare with reference commits
        self._compare_miner_commits(
            challenge=challenge,
            revealed_commits_list=new_commits,
            compare_with_each_other=False,
        )

    def _compare_miner_commits(
        self,
        challenge: str,
        revealed_commits_list: list[MinerChallengeCommit],
        compare_with_each_other: bool = False,
    ):
        """
        Compare miner commits for similarity checking.

        Args:
            challenge (str): Challenge name
            revealed_commits_list (list[MinerChallengeCommit]): Commits to compare
            compare_with_each_other (bool): If True, compares all commits with each other
                                          If False, only compares with reference commits

        Note: Used in two contexts:
        1. During regular scoring: compare_with_each_other=False to compare with reference commits
        2. At scoring hour: compare_with_each_other=True to compare all commits submitted within the same day with each other
        """
        if not revealed_commits_list:
            bt.logging.info(
                f"[CENTRALIZED SCORING] No commits for challenge: {challenge}, skipping"
            )
            return

        bt.logging.info(
            f"[CENTRALIZED SCORING] Running comparer for challenge: {challenge}"
        )
        comparer = self.active_challenges[challenge]["comparer"](
            challenge_name=challenge,
            challenge_info=self.active_challenges[challenge],
            miner_commits=revealed_commits_list,
            compare_with_each_other=compare_with_each_other,
        )
        # Run comparison, the comparer update commit 's penalty and comparison logs directly
        comparer.start_comparison()

        bt.logging.success(
            f"[CENTRALIZED SCORING] Comparison for challenge: {challenge} has been completed"
        )

    def run(self):
        bt.logging.info("Starting RewardApp loop.")
        # Try set weights after initial sync
        try:
            bt.logging.info("Initializing weights")
            self.set_weights()
        except Exception:
            bt.logging.error(f"Initial set weights error: {traceback.format_exc()}")

        while True:
            start_epoch = time.time()

            try:
                self.forward()
            except Exception as e:
                bt.logging.error(f"Forward error: {traceback.format_exc()}")

            end_epoch = time.time()
            elapsed = end_epoch - start_epoch
            time_to_sleep = max(0, self.config.reward_app.epoch_length - elapsed)
            bt.logging.info(f"Epoch finished. Sleeping for {time_to_sleep} seconds.")
            time.sleep(time_to_sleep)

            try:
                self.set_weights()
            except Exception:
                bt.logging.error(f"Set weights error: {traceback.format_exc()}")

            try:
                self.resync_metagraph()
            except Exception:
                bt.logging.error(f"Resync metagraph error: {traceback.format_exc()}")

            except KeyboardInterrupt:
                bt.logging.success("Keyboard interrupt detected. Exiting validator.")
                exit()

    # MARK: Commit Management
    def _update_validators_miner_commits(self):
        """
        Fetch all miner commits for challenges from all valid validators in the subnet.

        Process:
        1. Filter valid validators based on minimum stake requirement
        2. For each valid validator:
           - Fetch their latest miner commits from storage
           - Validate and process commits for active miners
           - Store in self.validators_miner_commits with validator (uid, hotkey) as key
        """
        # Get list of valid validators based on stake
        valid_validators = []
        for validator_uid, validator_ss58_address in enumerate(self.metagraph.hotkeys):
            stake = self.metagraph.S[validator_uid]
            if stake >= constants.MIN_VALIDATOR_STAKE:
                valid_validators.append((validator_uid, validator_ss58_address))

        bt.logging.info(
            f"[CENTRALIZED COMMIT UPDATES] Found {len(valid_validators)} valid validators"
        )

        # Initialize/clear validators_miner_commits for this round
        self.validators_miner_commits = {}

        for validator_uid, validator_hotkey in valid_validators:
            # Skip if request fails
            try:
                endpoint = f"{constants.STORAGE_URL}/fetch-latest-miner-commits"
                data = {
                    "validator_uid": validator_uid,
                    "validator_hotkey": validator_hotkey,
                    "challenge_names": list(self.active_challenges.keys()),
                }
                response = requests.post(
                    endpoint, headers=self.validator_request_header_fn(data), json=data
                )
                response.raise_for_status()
                # Only continue if response is successful
                data = response.json()
                this_validator_miner_commits: dict[
                    tuple[int, str], dict[str, MinerChallengeCommit]
                ] = {}
                # Process miner submissions for this validator
                for miner_hotkey, miner_commits in data["miner_commits"].items():
                    if miner_hotkey not in self.metagraph.hotkeys:
                        # Skip if miner hotkey is not in metagraph
                        continue

                    for challenge_name, miner_commit in miner_commits.items():
                        miner_commit = MinerChallengeCommit.model_validate(miner_commit)

                        this_validator_miner_commits.setdefault(
                            (miner_commit.miner_uid, miner_commit.miner_hotkey), {}
                        )[miner_commit.challenge_name] = miner_commit

                self.validators_miner_commits[(validator_uid, validator_hotkey)] = (
                    this_validator_miner_commits
                )
                bt.logging.success(
                    f"[CENTRALIZED COMMIT UPDATES] Fetched miner commits data from validator {validator_uid}, hotkey: {validator_hotkey}"
                )

            except Exception:
                bt.logging.warning(
                    f"[CENTRALIZED COMMIT UPDATES] Failed to fetch data for validator {validator_uid}, hotkey: {validator_hotkey}: {traceback.format_exc()}"
                )
                continue

        bt.logging.success(
            f"[CENTRALIZED COMMIT UPDATES] Updated validators_miner_submit with data from {len(self.validators_miner_commits)} validators"
        )

    def _update_miner_commits(self):
        """
        Aggregate miner commits from all validators into a single state.

        Process:
        1. Create new aggregated state from all validator commits
        2. For each miner/challenge:
           - Keep latest commit based on timestamp
           - For same encrypted_commit:
             * Use older commit timestamp
             * Preserve key and commit information
           - For different encrypted_commit:
             * Keep newer one based on timestamp
        3. Merge scoring data from existing state for unchanged commits
        4. Update self.miner_commits_cache for quick lookups
        """
        # Create new miner commits dict for aggregation
        new_miner_commits: dict[tuple[int, str], dict[str, MinerChallengeCommit]] = {}

        # Aggregate commits from all validators
        for _, miner_commits_from_validator in self.validators_miner_commits.items():
            for (
                miner_uid,
                miner_hotkey,
            ), miner_commits_in_challenges in miner_commits_from_validator.items():
                if miner_hotkey not in self.metagraph.hotkeys:
                    # Skip if miner hotkey is not in metagraph
                    continue

                miner_key = (miner_uid, miner_hotkey)

                # Initialize if first time seeing this miner
                if miner_key not in new_miner_commits:
                    new_miner_commits[miner_key] = miner_commits_in_challenges
                else:
                    # Update miner commits
                    for (
                        challenge_name,
                        miner_commit,
                    ) in miner_commits_in_challenges.items():
                        if challenge_name not in new_miner_commits[miner_key]:
                            new_miner_commits[miner_key][challenge_name] = miner_commit
                        else:
                            current_miner_commit = new_miner_commits[miner_key][
                                challenge_name
                            ]
                            if (
                                miner_commit.encrypted_commit
                                == current_miner_commit.encrypted_commit
                            ):
                                # If encrypted commit is the same, we update to older commit timestamp and add unknown commit and key field if possible
                                if (
                                    miner_commit.commit_timestamp
                                    and current_miner_commit.commit_timestamp
                                    and miner_commit.commit_timestamp
                                    < current_miner_commit.commit_timestamp
                                ):
                                    # Update to older commit timestamp
                                    current_miner_commit.commit_timestamp = (
                                        miner_commit.commit_timestamp
                                    )
                                if not current_miner_commit.key:
                                    # Add unknown key if possible
                                    current_miner_commit.key = miner_commit.key
                                if not current_miner_commit.commit:
                                    # Add unknown commit if possible
                                    current_miner_commit.commit = miner_commit.commit
                            else:
                                # If encrypted commit is different, we compare commit timestamp
                                if (
                                    miner_commit.commit_timestamp
                                    and current_miner_commit.commit_timestamp
                                    and miner_commit.commit_timestamp
                                    > current_miner_commit.commit_timestamp
                                ):
                                    # If newer commit timestamp, update to the latest commit
                                    current_miner_commit.commit_timestamp = (
                                        miner_commit.commit_timestamp
                                    )
                                else:
                                    # If older commit timestamp, skip
                                    continue

        # Merge scoring data from existing state
        for miner_key, existing_challenges in self.miner_commits.items():
            if miner_key not in new_miner_commits:
                continue

            for challenge_name, existing_commit in existing_challenges.items():
                if challenge_name not in new_miner_commits[miner_key]:
                    continue

                new_commit = new_miner_commits[miner_key][challenge_name]
                # If same encrypted commit, preserve stateful fields
                if existing_commit.encrypted_commit == new_commit.encrypted_commit:
                    new_commit.scoring_logs = existing_commit.scoring_logs
                    new_commit.comparison_logs = existing_commit.comparison_logs
                    new_commit.score = existing_commit.score
                    new_commit.penalty = existing_commit.penalty
                    new_commit.accepted = existing_commit.accepted
        self.miner_commits = new_miner_commits

        # Sort by UID to make sure all next operations are order consistent
        self.miner_commits = {
            (uid, ss58_address): commits
            for (uid, ss58_address), commits in sorted(
                self.miner_commits.items(), key=lambda item: item[0]
            )
        }

        # Update miner commits cache
        self.miner_commits_cache = {
            f"{commit.challenge_name}---{commit.encrypted_commit}": commit
            for _, commits in self.miner_commits.items()
            for commit in commits.values()
        }

    # MARK: Storage
    def _store_centralized_scoring(self, challenge_name: str = None):
        """
        Store scoring results to centralized storage.

        Args:
            challenge_name (str, optional): Specific challenge to store.
                                          If None, stores all challenges.

        Stores:
            - Challenge name
            - Docker hub ID
            - Scoring logs
            - Comparison logs
        """
        challenge_names = (
            [challenge_name] if challenge_name else list(self.scoring_results.keys())
        )
        endpoint = f"{constants.STORAGE_URL}/upload-centralized-score"

        all_scoring_results = []

        for challenge_name in challenge_names:
            scoring_results_to_send: list[dict] = []
            # Send batch of maximum 5 results at a time to avoid huge payload
            for docker_hub_id, result in self.scoring_results.get_all_for_challenge(
                challenge_name
            ).items():
                scoring_result = {
                    "challenge_name": challenge_name,
                    "docker_hub_id": docker_hub_id,
                    "scoring_logs": [
                        scoring_log.model_dump()
                        for scoring_log in result.get("scoring_logs", [])
                    ],
                    "comparison_logs": {
                        docker_hub_id: [
                            comparison_log.model_dump()
                            for comparison_log in _comparison_logs
                        ]
                        for docker_hub_id, _comparison_logs in result.get(
                            "comparison_logs", {}
                        ).items()
                    },
                }
                scoring_results_to_send.append(scoring_result)
                all_scoring_results.append(scoring_result)

                if len(scoring_results_to_send) >= 5:
                    try:
                        data = {"scoring_results": scoring_results_to_send}
                        response = requests.post(
                            endpoint,
                            headers=self.validator_request_header_fn(data),
                            json=data,
                        )
                        response.raise_for_status()
                        scoring_results_to_send = []
                    except Exception:
                        bt.logging.error(
                            f"Failed to send scoring results to storage: {traceback.format_exc()}"
                        )
                        scoring_results_to_send = []

            if scoring_results_to_send:
                try:
                    data = {"scoring_results": scoring_results_to_send}
                    response = requests.post(
                        endpoint,
                        headers=self.validator_request_header_fn(data),
                        json=data,
                    )
                    response.raise_for_status()
                except Exception:
                    bt.logging.error(
                        f"Failed to send scoring results to storage: {traceback.format_exc()}"
                    )

        if all_scoring_results:
            try:
                with open("scoring_results.json", "w") as f:
                    json.dump(all_scoring_results, f)
            except Exception:
                bt.logging.error(
                    f"Failed to save scoring results to file: {traceback.format_exc()}"
                )

    def _initialize_scoring_cache(self):
        """
        Initialize the scoring LRU cache with the most recent data from centralized storage.
        Uses the limit parameter to get only the most recent data per challenge.
        """
        bt.logging.info(
            "[CENTRALIZED SCORING] Initializing scoring LRU cache from storage"
        )

        # Process each challenge separately to manage memory usage
        for challenge_name in self.active_challenges.keys():
            try:
                # Request the most recent entries for this challenge
                entries_per_challenge = 256  # Match the LRU cache size

                endpoint = f"{constants.STORAGE_URL}/fetch-centralized-score"
                data = {
                    "challenge_names": [challenge_name],
                    "limit": entries_per_challenge,  # Get the most recent entries
                    "full_results": False,  # Apply date filtering for recency
                    "get_detailed_results": True,  # Get full details
                }

                bt.logging.info(
                    f"[CENTRALIZED SCORING] Fetching up to {entries_per_challenge} scoring results for challenge {challenge_name}"
                )

                response = requests.post(
                    endpoint, headers=self.validator_request_header_fn(data), json=data
                )
                response.raise_for_status()
                results = response.json()["data"]

                if not results:
                    bt.logging.info(
                        f"[CENTRALIZED SCORING] No scoring results found for challenge {challenge_name}"
                    )
                    continue

                loaded_count = 0
                for result in results:
                    processed_result = {
                        "scoring_logs": [
                            ScoringLog.model_validate(scoring_log)
                            for scoring_log in result["scoring_logs"]
                        ],
                        "comparison_logs": {
                            docker_hub_id: [
                                ComparisonLog.model_validate(comparison_log)
                                for comparison_log in _comparison_logs
                            ]
                            for docker_hub_id, _comparison_logs in result[
                                "comparison_logs"
                            ].items()
                        },
                    }

                    # Store in our LRU cache
                    self.scoring_results.set(
                        challenge=challenge_name,
                        docker_hub_id=result["docker_hub_id"],
                        result=processed_result,
                    )
                    loaded_count += 1

                bt.logging.info(
                    f"[CENTRALIZED SCORING] Loaded {loaded_count} scoring results for challenge {challenge_name}"
                )

            except Exception as e:
                bt.logging.error(
                    f"[CENTRALIZED SCORING] Error initializing scoring cache for challenge {challenge_name}: {traceback.format_exc()}"
                )

        # Log statistics about the populated cache
        stats = self.scoring_results.get_stats()
        bt.logging.info(
            f"[CENTRALIZED SCORING] Cache initialized with {stats['total_entries']} total entries"
        )
        bt.logging.info(
            f"[CENTRALIZED SCORING] Cache entries per challenge: {stats['challenge_counts']}"
        )

    def _sync_scoring_results_from_storage_to_cache(self):
        """
        Sync scoring results (self.scoring_results) from storage to cache.
        This method will update the cache with scoring results from storage.
        """
        # Iter all the keys in all cache corespond to active challenges
        for challenge_name in self.active_challenges.keys():
            diskcache_ = self.storage_manager._get_cache(challenge_name)
            memcache_ = self.scoring_results.get_all_for_challenge(challenge_name)
            cache_keys_to_delete = []

            for hashed_cache_key in diskcache_.iterkeys():
                commit = diskcache_.get(hashed_cache_key)
                try:
                    commit = MinerChallengeCommit.model_validate(
                        commit
                    )  # Model validate the commit
                except Exception:
                    # Skip if commit is not valid
                    # Do this if we want to clean up invalid commits
                    # cache_keys_to_delete.append(hashed_cache_key)
                    continue

                # Check if docker_hub_id is in self.scoring_results
                if commit.docker_hub_id not in memcache_:
                    # Do this if we want to clean up commits with no scoring results
                    # cache_keys_to_delete.append(hashed_cache_key)
                    continue

                # Found the commit in self.scoring_results, now we make sure cache have correct scoring_logs
                if not commit.scoring_logs:
                    # If not scoring_logs, we add the scoring_logs from self.scoring_results
                    commit.scoring_logs = memcache_[commit.docker_hub_id][
                        "scoring_logs"
                    ]
                    diskcache_[hashed_cache_key] = commit.model_dump()
                else:
                    # Check for each entries in scoring_logs for miner_input and miner_output, they should not be None
                    scoring_logs_with_none = []
                    for scoring_log in commit.scoring_logs:
                        if (
                            scoring_log.miner_input is None
                            or scoring_log.miner_output is None
                        ):
                            scoring_logs_with_none.append(scoring_log)

                    # If there are any scoring logs with None, we use the scoring_logs from self.scoring_results and update the cache
                    if any(scoring_logs_with_none):
                        commit.scoring_logs = memcache_[commit.docker_hub_id][
                            "scoring_logs"
                        ]
                        diskcache_[hashed_cache_key] = commit.model_dump()

            # Clean up cache entries that we want to delete
            for hashed_cache_key in cache_keys_to_delete:
                diskcache_.delete(hashed_cache_key)

    # MARK: Endpoints
    async def get_scoring_result(
        self,
        challenge_name: Annotated[str, Body(..., embed=True)],
        encrypted_commits: Annotated[list[str], Body(..., embed=True)],
    ):
        """
        API endpoint to get scoring logs for specific docker hub IDs.
        This method check for encrypted_commit in miner_commits and return the cached commit result.

        Args:
            docker_hub_ids: List of docker hub IDs to look up

        Returns:
            dict: {
                docker_hub_id: scoring_log or None if not found
            }
        """
        assert (
            challenge_name in self.active_challenges
        ), f"Challenge {challenge_name} is not active"

        results: dict[str, MinerChallengeCommit] = {}

        for encrypted_commit in encrypted_commits:
            # Try in-memory cache first
            cache_key = f"{challenge_name}---{encrypted_commit}"
            commit_result = self.miner_commits_cache.get(cache_key, None)
            if commit_result:
                results[encrypted_commit] = commit_result.public_view()
                continue

            # Fallback to disk cache
            try:
                hashed_cache_key = self.storage_manager.hash_cache_key(encrypted_commit)
                challenge_cache = self.storage_manager._get_cache(challenge_name)
                cached_data = challenge_cache.get(hashed_cache_key)

                if cached_data:
                    commit_result = MinerChallengeCommit.model_validate(cached_data)
                    results[encrypted_commit] = commit_result.public_view()
                else:
                    results[encrypted_commit] = None
            except Exception as e:
                bt.logging.error(f"Error retrieving from disk cache: {e}")
                results[encrypted_commit] = None

        return {
            "status": "success",
            "message": "Scoring results retrieved successfully",
            "data": {
                "commits": results,
                "is_done": self.is_scoring_done.get(challenge_name),
            },
        }


if __name__ == "__main__":
    # Initialize and run app
    with RewardApp(get_reward_app_config()) as app:
        while True:
            bt.logging.info("RewardApp is running...")
            time.sleep(constants.EPOCH_LENGTH // 4)
