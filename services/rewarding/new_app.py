import argparse
import datetime
import os
import threading
import time
import traceback
from typing import Annotated, Union

import bittensor as bt
import requests
import uvicorn
from fastapi import Body, FastAPI
from pydantic import BaseModel

from neurons.validator.validator import (
    ChallengeManager,
    MinerManager,
    ScoringLog,
    StorageManager,
    Validator,
    start_bittensor_log_listener,
)
from redteam_core import challenge_pool, constants
from redteam_core.common import get_config
from redteam_core.validator.models import MinerChallengeCommit, ComparisonLog

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
    2. Maintains challenge records like regular validators
    3. Scores miner submissions from storage
    4. Provides API endpoints for direct access to scoring results
    """

    def __init__(self, config: bt.Config):
        """Initialize the reward app with validator capabilities."""
        super().__init__(config)
        # Initialize validator state
        self.validators_miner_commits: dict[
            tuple[int, str], dict[tuple[int, str], dict[str, MinerChallengeCommit]]
        ] = {}  # Stores current miner commits from all validators
        # Daily miner commits will now stored in self.miner_commits
        # Quick lookup for miner commits by encrypted_commit
        self.miner_commits_cache: dict[str, MinerChallengeCommit] = {}
        # Cache for scored docker_hub_ids, map from string to the coresponding "scoring_logs" and "comparison_logs"
        self.scoring_cache: dict[
            str, dict[str, Union[list[ScoringLog], dict[str, ComparisonLog]]]
        ] = {
            challenge_name: self._fetch_centralized_scoring(challenge_name)
            for challenge_name in self.active_challenges.keys()
        }

        # Initialize FastAPI app
        self.app = FastAPI()
        self.app.add_api_route(
            "/get_scoring_result",
            self.get_scoring_result,
            methods=["POST"],
        )
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
        bt.logging.info(f"FastAPI server is running on port {self.config.port}!")

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
        """
        Main validation loop:
        1. Fetch new submissions from storage
        2. Score and do similarity check for new submissions (every forward)
        4. Store results back to storage
        """
        # Update submissions from all validators
        self._update_validators_miner_commits()
        # Update miner commits
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

        # Score and store miner commits for each challenge
        for challenge in revealed_commits:
            if revealed_commits[challenge]:
                # Score and compare submissions efficiently using cached result

                # Split commits into new and cached
                new_commits: list[MinerChallengeCommit] = []
                for commit in revealed_commits[challenge]:
                    if commit.docker_hub_id in self.scoring_cache[challenge]:
                        # Use cached results
                        cached_result = self.scoring_cache[challenge][commit.docker_hub_id]
                        commit.scoring_logs = cached_result['scoring_logs']
                        commit.comparison_logs = cached_result['comparison_logs']
                    else:
                        new_commits.append(commit)

                if not new_commits:
                    return

                self._score_miner_commits(
                    challenge=challenge,
                    revealed_commits_list=new_commits,
                )
                # Compare new commits with previous unique commits only
                self._compare_miner_commits(
                    challenge=challenge,
                    revealed_commits_list=revealed_commits[challenge],
                    compare_with_each_other=False,
                )

                # Update cache
                for commit in new_commits:
                    self.scoring_cache[challenge][commit.docker_hub_id] = {
                        "scoring_logs": commit.scoring_logs,
                        "comparison_logs": commit.comparison_logs
                    }

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

        # Check if it's time to finalize validator's daily state
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
            # Update scores and penalties to challenge manager
            for challenge in revealed_commits:
                self.challenge_managers[challenge].update_miner_scores(
                    revealed_commits_list=revealed_commits[challenge]
                )
            # Store challenge records and update state
            self.scoring_dates.append(today_key)
            self.store_challenge_records_new(dates=today_key)
        else:
            bt.logging.debug(
                f"[CENTRALIZED FORWARD] Not time to finalize daily result. Hour: {current_hour}, Date: {today_key}"
            )

    def _score_miner_commits(
        self, challenge: str, revealed_commits_list: list[MinerChallengeCommit]
    ):
        """
        Score miner commits for all challenges.
        """
        bt.logging.info("[CENTRALIZED SCORING] Scoring miner commits")
        if challenge not in self.active_challenges:
            return
        if not revealed_commits_list:
            bt.logging.info(
                f"[CENTRALIZED SCORING] No commits for challenge: {challenge}"
            )
            return

        bt.logging.info(
            f"[CENTRALIZED SCORING] Running controller for challenge: {challenge}"
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
        challenge_local_cache = self.storage_manager.local_caches.get(challenge)
        if challenge_local_cache:
            unique_commits_cached_data_raw = [
                challenge_local_cache.get(unique_commit_cache_key)
                for unique_commit_cache_key in unique_commits_cache_keys
            ]
            unique_commits_cached_data = [
                MinerChallengeCommit(**commit)
                for commit in unique_commits_cached_data_raw
                if commit
            ]

        # 2. Run challenge controller
        bt.logging.info(
            f"[CENTRALIZED SCORING] Running controller for challenge: {challenge}"
        )
        # This challenge controll will run with new inputs and reference commit input
        # Reference commits are collected from yesterday, so if same docker_hub_id commited same day, they can share comparison_logs field, and of course, scoring_logs field
        # If same docker_hub_id commited different day, the later one expected to be ignored anyway
        controller = self.active_challenges[challenge]["controller"](
            challenge_name=challenge,
            miner_commits=revealed_commits_list,
            reference_comparison_commits=unique_commits_cached_data,
            challenge_info=self.active_challenges[challenge],
        )
        # Run challenge controller, the controller update commit 's scoring logs and reference comparison logs directly
        controller.start_challenge()

    def _compare_miner_commits(
        self,
        challenge: str,
        revealed_commits_list: list[MinerChallengeCommit],
        compare_with_each_other: bool = False,
    ):
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
            f"[CENTRALIZED SCORING] Scoring  for challenge: {challenge} has been completed"
        )

    def run(self):
        bt.logging.info("Starting RewardApp loop.")
        while True:
            start_epoch = time.time()

            try:
                self.forward()
            except Exception as e:
                bt.logging.error(f"Forward error: {e}")
                traceback.print_exc()

            end_epoch = time.time()
            elapsed = end_epoch - start_epoch
            time_to_sleep = max(0, self.config.reward_app.epoch_length - elapsed)
            bt.logging.info(f"Epoch finished. Sleeping for {time_to_sleep} seconds.")
            time.sleep(time_to_sleep)

            try:
                self.resync_metagraph()
            except Exception as e:
                bt.logging.error(f"Resync metagraph error: {e}")
                traceback.print_exc()

            except KeyboardInterrupt:
                bt.logging.success("Keyboard interrupt detected. Exiting validator.")
                exit()

    # MARK: Commit Management
    def _update_validators_miner_commits(self):
        """
        Fetch all miner_submit for challenges from all valid validators in the subnet.
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
                endpoint = constants.STORAGE_URL + "/fetch-latest-miner-commits"
                data = {
                    "validator_uid": validator_uid,
                    "validator_hotkey": validator_hotkey,
                    "challenge_names": list(self.active_challenges.keys()),
                }
                response = requests.post(endpoint, json=data)
                response.raise_for_status()
                # Only continue if response is successful
                data = response.json()
                this_validator_miner_commits: dict[
                    tuple[int, str], dict[str, MinerChallengeCommit]
                ] = {}
                # Process miner submissions for this validator
                for miner_hotkey, miner_commits_in_challenges in data[
                    "miner_commits"
                ].items():
                    if miner_hotkey not in self.metagraph.hotkeys:
                        # Skip if miner hotkey is not in metagraph
                        continue

                    for (
                        challenge_name,
                        miner_commit,
                    ) in miner_commits_in_challenges.items():
                        miner_commit = MinerChallengeCommit.model_validate(miner_commit)

                        this_validator_miner_commits[
                            (miner_commit.miner_uid, miner_commit.miner_hotkey)
                        ][challenge_name] = miner_commit

                # TODO: Think about what to use as validators_miner_submit keys
                self.validators_miner_commits[(validator_uid, validator_hotkey)] = (
                    this_validator_miner_commits
                )
                bt.logging.success(
                    f"[CENTRALIZED COMMIT UPDATES] Fetched miner commits data from validator {validator_uid}, hotkey: {validator_hotkey}"
                )

            except Exception as e:
                bt.logging.warning(
                    f"[CENTRALIZED COMMIT UPDATES] Failed to fetch data for validator {validator_uid}, hotkey: {validator_hotkey}: {str(e)}"
                )
                continue

        bt.logging.success(
            f"[CENTRALIZED COMMIT UPDATES] Updated validators_miner_submit with data from {len(self.validators_miner_commits)} validators"
        )

    def _update_miner_commits(self):
        """
        Update miner commits by aggregating commits from all validators.
        For each miner/challenge, keep only the latest commit based on commit_timestamp,
        while preserving key and commit information from other validators if available.
        """
        # # Create new miner commits dict for aggregation
        new_miner_commits: dict[tuple[int, str], dict[str, MinerChallengeCommit]] = {}

        # Aggregate commits from all validators
        for (
            validator_uid,
            validator_hotkey,
        ), miner_commits_from_validator in self.validators_miner_commits.items():
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
                                    miner_commit.commit_timestamp = (
                                        current_miner_commit.commit_timestamp
                                    )
                                if not current_miner_commit.key:
                                    # Add unknown key if possible
                                    miner_commit.key = current_miner_commit.key
                                if not current_miner_commit.commit:
                                    # Add unknown commit if possible
                                    miner_commit.commit = current_miner_commit.commit
                            else:
                                # If encrypted commit is different, we compare commit timestamp
                                if (
                                    miner_commit.commit_timestamp
                                    and current_miner_commit.commit_timestamp
                                    and miner_commit.commit_timestamp
                                    > current_miner_commit.commit_timestamp
                                ):
                                    # If newer commit timestamp, update to the latest commit
                                    miner_commit.commit_timestamp = (
                                        current_miner_commit.commit_timestamp
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
        Store the centralized scoring cache to a centralized collection
        """
        challenge_names = [challenge_name] if challenge_name else list(self.scoring_cache.keys())
        endpoint = constants.STORAGE_URL + "/upload-centralized-scoring"
        data = {
            "scoring_results": [
                {
                    "challenge_name": challenge_name,
                    "docker_hub_id": docker_hub_id,
                    "scoring_logs": result.get("scoring_logs", []),
                    "comparison_logs": result.get("comparison_logs", {})
                }
                for challenge_name in challenge_names
                for docker_hub_id, result in self.scoring_cache.get(challenge_name, {}).items()
            ]
        }

        response = requests.post(
            endpoint,
            headers=self.validator_request_header_fn(data),
            json=data
        )
        response.raise_for_status()

    def _fetch_centralized_scoring(self, challenge_names: list[str] = []) -> dict[str, dict[str, Union[list[ScoringLog], dict[str, ComparisonLog]]]]:
        """
        Fetch the centralized scoring cache from a centralized collection
        """
        if not challenge_names:
            # Fetch all challenges
            challenge_names = list(self.active_challenges.keys())

        endpoint = constants.STORAGE_URL + "/fetch-centralized-scoring"
        data = {
            "challenge_names": challenge_names,
        }
        response = requests.post(
            endpoint,
            headers=self.validator_request_header_fn(data),
            json=data
        )
        response.raise_for_status()
        return response.json()

    # MARK: Helper Methods
    def get_unscored_miner_submissions(self) -> dict[int, dict[str, list[dict]]]:
        """
        Filter out submissions that haven't been scored yet from validators_miner_submit.
        For duplicate submissions (same encrypted_commit), keep the one with latest commit_timestamp
        but preserve other fields.
        """
        # Temporary structure to track unique submissions
        temp_submissions = {}

        for validator_uid, miner_submissions in self.validators_miner_commits.items():
            for miner_uid, challenges in miner_submissions.items():
                for challenge_name, submission in challenges.items():
                    if challenge_name not in self.active_challenges:
                        continue

                    if not submission.get("encrypted_commit"):
                        continue

                    # TODO: SHOULD WE RENEW "LOG" FIELD ?
                    # Remove log field to rely only on cache for scoring check
                    submission_copy = {
                        k: v for k, v in submission.items() if k != "log"
                    }
                    submission_copy["log"] = {}

                    if not self._is_submission_scored(challenge_name, submission_copy):
                        temp_submissions.setdefault(miner_uid, {}).setdefault(
                            challenge_name, {}
                        )

                        encrypted_commit = submission["encrypted_commit"]
                        existing = temp_submissions[miner_uid][challenge_name].get(
                            encrypted_commit
                        )

                        if existing:
                            # Update timestamp if newer
                            if (
                                submission["commit_timestamp"]
                                > existing["commit_timestamp"]
                            ):
                                existing["commit_timestamp"] = submission[
                                    "commit_timestamp"
                                ]

                            # Update other fields if they become available
                            for field in ["commit", "key"]:
                                if not existing.get(field) and submission.get(field):
                                    existing[field] = submission[field]
                        else:
                            # Add new submission
                            temp_submissions[miner_uid][challenge_name][
                                encrypted_commit
                            ] = submission_copy

        # Convert to final structure with lists
        unscored_submissions = {}
        for miner_uid, challenges in temp_submissions.items():
            unscored_submissions[miner_uid] = {
                challenge_name: list(submissions.values())
                for challenge_name, submissions in challenges.items()
            }

        return unscored_submissions

    def _is_submission_scored(self, challenge_name: str, submission: dict) -> bool:
        """
        Check if a submission has been scored by looking at its cache entry.

        Args:
            challenge_name (str): Name of the challenge
            submission (dict): Submission data containing encrypted_commit

        Returns:
            bool: True if submission has been scored, False otherwise
        """
        if not submission.get("encrypted_commit"):
            return False

        # Check cache for scoring logs
        hashed_cache_key = self.storage_manager.hash_cache_key(
            submission["encrypted_commit"]
        )
        cache = self.storage_manager._get_cache(challenge_name)
        cached_submission = cache.get(hashed_cache_key)

        return bool(cached_submission and cached_submission.get("log"))

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
        assert challenge_name in self.active_challenges, (
            f"Challenge {challenge_name} is not active"
        )

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

    async def get_challenge_records(self, challenge_name: str):
        """API endpoint to get challenge records."""
        if challenge_name in self.miner_managers:
            return self.miner_managers[challenge_name].challenge_records
        return {}


if __name__ == "__main__":
    # Initialize and run app
    with RewardApp(get_reward_app_config()) as app:
        while True:
            bt.logging.info("RewardApp is running...")
            time.sleep(constants.EPOCH_LENGTH // 4)
