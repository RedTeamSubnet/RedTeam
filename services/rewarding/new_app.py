import os
import time
import argparse
import datetime
import traceback
import requests
import threading
from typing import Optional
from collections import defaultdict
from itertools import chain

import uvicorn
import bittensor as bt
from pydantic import BaseModel
from fastapi import FastAPI

from neurons.validator.validator import Validator
from redteam_core import (
    BaseValidator,
    challenge_pool,
    constants,
    MinerManager,
    StorageManager,
    ScoringLog,
)
from redteam_core.common import get_config

REWARD_APP_SS58_ADDRESS = os.getenv("REWARD_APP_SS58_ADDRESS")
REWARD_APP_UID = -1

def get_reward_app_config() -> bt.Config:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=47920)
    parser.add_argument("--reward_app_epoch_length", type=int, default=60)
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
        # Initialize BaseValidator with some moddification
        self.config = config
        self.setup_logging()
        self.setup_bittensor_objects()
        self.last_update = 0
        self.current_block = 0
        # We can get ss58_address with "self.wallet.hotkey.ss58_address"
        self.ss58_address = REWARD_APP_SS58_ADDRESS
        self.uid = REWARD_APP_SS58_ADDRESS
        self.is_running = False

        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.miner_managers = {
            challenge: MinerManager(
                challenge_name=challenge,
                challenge_incentive_weight=self.active_challenges[challenge]["challenge_incentive_weight"],
                metagraph=self.metagraph
            )
            for challenge in self.active_challenges.keys()
        }

        self.storage_manager = StorageManager(
            cache_dir=self.config.validator.cache_dir,
            hf_repo_id=self.config.validator.hf_repo_id,
            sync_on_init=True
        )

        # Initialize validator state
        self.validators_miner_submit = {}  # Stores current miner submissions from all validators
        self.daily_miner_submissions = {}  # Stores all submissions for today
        self.scoring_dates: list[str] = []
        self._init_challenge_records_from_subnet()
        self._init_validators_miner_submit_from_subnet()

        # Initialize FastAPI app
        self.app = FastAPI()
        self.app.add_api_route("/get_scoring_logs", self.get_scoring_logs, methods=["POST"], response_model=dict[str, Optional[list[dict]]])
        self.app.add_api_route("/get_challenge_records", self.get_challenge_records, methods=["GET"])
        # Run FastAPI server in a separate thread
        self.server_thread = threading.Thread(
            target=uvicorn.run,
            kwargs={
                "app": self.app,
                "host": "0.0.0.0",
                "port": self.config.port,
                "log_level": "debug"
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

    def _init_validators_miner_submit_from_subnet(self):
        pass

    # MARK: Validation Loop
    def forward(self):
        """
        Main validation loop:
        1. Fetch new submissions from storage
        2. Score unscored submissions (every forward)
        3. Update challenge records (once per day at scoring hour)
        4. Store results back to storage
        """
        # Update submissions from all validators
        self._update_validators_miner_commit(self.active_challenges)

        # Get unscored submissions and their revealed commits
        unscored_submissions = self.get_unscored_miner_submissions()
        revealed_commits = self.get_revealed_commits(unscored_submissions)

        # Always score unscored submissions
        if revealed_commits:
            bt.logging.info(f"[FORWARD] Scoring new submissions")
            # Score submissions efficiently using cache
            all_challenge_logs = self._score_submissions(revealed_commits)

            # Update submissions with new logs and store them
            updated_submissions = self._update_miner_scoring_logs(
                all_challenge_logs=all_challenge_logs,
                unscored_submissions=unscored_submissions
            )
            self._store_miner_commits(updated_submissions)

        # Check if it's time to create daily challenge records
        # Get current time info
        today = datetime.datetime.now(datetime.timezone.utc)
        today_key = today.strftime("%Y-%m-%d")
        current_hour = today.hour

        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates

        if validate_scoring_hour and validate_scoring_date:
            bt.logging.info(f"[FORWARD] Creating challenge records for {today_key}")
            # Update daily submissions
            self._update_daily_submissions()
            # Get scoring logs from cache for daily submissions
            challenge_logs = self._get_scoring_logs_from_daily_submissions()

            # Update scores for each challenge
            for challenge_name, logs in challenge_logs.items():
                if logs:  # Only update if we have logs
                    self.miner_managers[challenge_name].update_scores(logs)

            # Store challenge records and update state
            self.scoring_dates.append(today_key)
            self.store_challenge_records_new(dates=today_key)
        else:
            bt.logging.debug(f"[FORWARD] Not time for challenge records yet. Hour: {current_hour}, Date: {today_key}")

    def _score_submissions(self, revealed_commits: dict[str, tuple[list[str], list[int]]]) -> dict[str, list[ScoringLog]]:
        """
        Score submissions efficiently by reusing cached scores for previously seen docker images.

        Args:
            revealed_commits: {
                challenge_name: ([docker_hub_ids], [miner_uids])
            }

        Returns:
            dict: {
                challenge_name: [ScoringLog objects]
            }
        """
        all_challenge_logs: dict[str, list[ScoringLog]] = {}

        for challenge_name, (docker_hub_ids, miner_uids) in revealed_commits.items():
            if challenge_name not in self.active_challenges:
                continue

            bt.logging.info(f"[SCORING] Processing challenge: {challenge_name}")

            # Separate docker images into cached and new
            docker_score_cache = self.storage_manager._get_cache("_docker_hub_id_score_log")
            cached_logs = []
            new_docker_ids = []

            for docker_id in docker_hub_ids:
                cached_log = docker_score_cache.get(f"{challenge_name}---{docker_id}")
                if cached_log:
                    cached_logs.extend(cached_log)
                else:
                    new_docker_ids.append(docker_id)

            # Score new docker images if any exist
            new_logs = self._score_new_docker_images(
                challenge_name, new_docker_ids
            ) if new_docker_ids else []

            # Map scores to individual miners
            docker_uid_map = defaultdict(list)
            for docker_hub_id, miner_uid in zip(docker_hub_ids, miner_uids):
                docker_uid_map[docker_hub_id].append(miner_uid)

            challenge_logs = []

            # Process all logs (both cached and new)
            for log in chain(cached_logs, new_logs):
                for miner_uid in docker_uid_map[log["miner_docker_image"]]:
                    miner_log = ScoringLog(**log)
                    miner_log.uid = miner_uid
                    challenge_logs.append(miner_log)

            if challenge_logs:
                all_challenge_logs[challenge_name] = challenge_logs

        return all_challenge_logs

    def _score_new_docker_images(self, challenge_name: str, docker_hub_ids: list[str]) -> list[dict]:
        """
        Score new docker images and cache their results.

        Args:
            challenge_name: Name of the challenge
            docker_hub_ids: List of docker hub IDs to score

        Returns:
            list: List of dict objects for new scores
        """
        bt.logging.info(f"[SCORING] Scoring {len(docker_hub_ids)} new docker images for {challenge_name}")

        # Create controller and score
        controller = self.active_challenges[challenge_name]["controller"](
            challenge_name=challenge_name,
            miner_docker_images=docker_hub_ids,
            uids=[999] * len(docker_hub_ids),  # Placeholder UID
            challenge_info=self.active_challenges[challenge_name]
        )
        logs = controller.start_challenge()
        # Cache new scores
        docker_score_cache = self.storage_manager._get_cache("_docker_hub_id_score_log")
        for log in logs:
            cache_key = f"{challenge_name}---{log['miner_docker_image']}"
            if cache_key in docker_score_cache:
                docker_score_cache[cache_key].append(log)
            else:
                docker_score_cache[cache_key] = [log]

        return logs

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
            time_to_sleep = max(0, self.config.reward_app_epoch_length - elapsed)
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
    # TODO: Check can we use uid instead of ss58_address for miner_submit keys
    def _update_validators_miner_commit(self, active_challenges) -> list[dict]:
        """
        Fetch all miner_submit for challenges from all valid validators in the subnet.
        """
        # Get list of valid validators based on stake
        valid_validators = []
        for validator_uid, validator_ss58_address in enumerate(self.metagraph.hotkeys):
            stake = self.metagraph.S[validator_uid]
            if stake >= constants.MIN_VALIDATOR_STAKE:
                valid_validators.append((validator_uid, validator_ss58_address))

        bt.logging.info(f"[FORWARD] Found {len(valid_validators)} valid validators")

        # Initialize/clear validators_miner_submit for this round
        self.validators_miner_submit = {}

        for validator_uid, validator_hotkey in valid_validators:
            # Skip if request fails
            try:
                endpoint = constants.STORAGE_URL + "/fetch-miner-submit"
                data = {
                    "validator_ss58_address": validator_hotkey,
                    "validator_uid": validator_uid,
                    "challenge_names": list(active_challenges.keys())
                }
                response = requests.post(endpoint, json=data)
                response.raise_for_status()
                # Only continue if response is successful
                data = response.json()
                miner_submit = {}
                # Process miner submissions for this validator
                for ss58_address, challenges in data["miner_submit"].items():
                    if ss58_address in self.metagraph.hotkeys:
                        miner_uid = self.metagraph.hotkeys.index(ss58_address)
                        for challenge_name, commit_data in challenges.items():
                            miner_submit.setdefault(miner_uid, {})[challenge_name] = {
                                "commit_timestamp": commit_data["commit_timestamp"],
                                "encrypted_commit": commit_data["encrypted_commit"],
                                "key": commit_data["key"],
                                "commit": commit_data["commit"],
                                "log": commit_data.get("log", {})
                            }

                # TODO: Think about what to use as validators_miner_submit keys
                self.validators_miner_submit[validator_uid] = miner_submit
                bt.logging.success(f"[FORWARD] Fetched miner submit data from validator {validator_uid}")

            except Exception as e:
                bt.logging.warning(f"[FORWARD] Failed to fetch data for validator {validator_uid}: {str(e)}")
                continue

        bt.logging.success(f"[FORWARD] Updated validators_miner_submit with data from {len(self.validators_miner_submit)} validators")

    def _get_scoring_logs_from_daily_submissions(self) -> dict[str, list[ScoringLog]]:
        """
        Get scoring logs from cache for all submissions in daily_miner_submissions.
        Groups logs by challenge name for easier processing.

        Returns:
            dict: {
                challenge_name: [ScoringLog objects]
            }
        """
        challenge_logs = {}

        for miner_uid, challenges in self.daily_miner_submissions.items():
            for challenge_name, submission in challenges.items():
                if challenge_name not in self.active_challenges:
                    continue

                if not submission.get("encrypted_commit"):
                    continue

                # Get logs from cache
                hashed_cache_key = self.storage_manager.hash_cache_key(submission["encrypted_commit"])
                cache = self.storage_manager._get_cache(challenge_name)
                cached_submission = cache.get(hashed_cache_key)

                if cached_submission and cached_submission.get("log"):
                    # Initialize challenge logs list if needed
                    if challenge_name not in challenge_logs:
                        challenge_logs[challenge_name] = []

                    # Convert cache logs to ScoringLog objects
                    for log_entry in cached_submission["log"].values():
                        for log_data in log_entry:
                            log_data["uid"] = miner_uid
                            # Get docker_hub_id from commit if available
                            if submission.get("commit"):
                                log_data["miner_docker_image"] = submission["commit"].split("---")[1]
                            challenge_logs[challenge_name].append(ScoringLog(**log_data))

        return challenge_logs

    def _update_miner_scoring_logs(self, all_challenge_logs: dict[str, list[ScoringLog]], unscored_submissions: dict[int, dict[str, list[dict]]]) -> dict[int, dict[str, list[dict]]]:
        """
        Updates unscored submissions with new scoring logs in place.
        Each submission will get a fresh log entry for today.

        Args:
            all_challenge_logs (dict): Dictionary of challenge names and lists of ScoringLog objects
            unscored_submissions (dict): Output from get_unscored_miner_submissions()

        Returns:
            dict: The same unscored_submissions object with logs added
        """
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

        for challenge_name, logs in all_challenge_logs.items():
            for log in logs:
                miner_uid = log.uid
                if miner_uid not in unscored_submissions:
                    continue

                # Find matching submission for this log
                for submission in unscored_submissions[miner_uid].get(challenge_name, []):
                    # TODO: CHECK IF THIS MATCHIG LOGIC CORRECT
                    if submission.get("commit") == f"{challenge_name}---{log.miner_docker_image}":
                        # Add today's log directly to the submission
                        if today not in submission["log"]:
                            submission["log"][today] = []
                        submission["log"][today].append(log.model_dump())

        return unscored_submissions

    def _update_daily_submissions(self):
        """
        Update daily submissions by aggregating submissions from all validators.
        For each miner/challenge, keep only the latest submission based on commit_timestamp.
        """
        # Reset daily submissions
        new_daily_submissions = {}

        # Aggregate submissions from all validators
        for validator_uid, miner_submissions in self.validators_miner_submit.items():
            for miner_uid, challenges in miner_submissions.items():
                for challenge_name, submission in challenges.items():
                    if challenge_name not in self.active_challenges:
                        continue

                    current_timestamp = submission.get("commit_timestamp", 0)

                    # Initialize if needed
                    if miner_uid not in new_daily_submissions:
                        new_daily_submissions[miner_uid] = {}

                    # Check existing submission
                    existing = new_daily_submissions[miner_uid].get(challenge_name)

                    # TODO: CHECK THIS AGREGATION LOGIC AGAIN
                    # Update if this is the first submission or if it's newer
                    if not existing or current_timestamp > existing.get("commit_timestamp", 0):
                        new_daily_submissions[miner_uid][challenge_name] = submission

        self.daily_miner_submissions = new_daily_submissions

    # MARK: Storage
    def _store_miner_commits(self, miner_submissions: dict[int, dict[str, list[dict]]]):
        """
        Store updated miner submissions to storage.

        Args:
            updated_submissions (dict): Output from _update_miner_scoring_logs()
        """
        data_to_store: list[dict] = []

        for miner_uid, challenges in miner_submissions.items():
            miner_ss58_address = self.metagraph.hotkeys[miner_uid]
            for challenge_name, submissions in challenges.items():
                for submission in submissions:
                    # Construct data
                    data = {
                        "miner_uid": int(miner_uid),
                        "miner_ss58_address": miner_ss58_address,
                        "validator_uid": -1,  # Special UID for RewardApp
                        "validator_ss58_address": self.wallet.hotkey.ss58_address,
                        "challenge_name": challenge_name,
                        "commit_timestamp": submission["commit_timestamp"],
                        "encrypted_commit": submission["encrypted_commit"],
                        "key": submission["key"],
                        "commit": submission["commit"],
                        "log": submission.get("log", {})
                    }
                    # Sign the submission
                    self._sign_with_private_key(data=data)
                    data_to_store.append(data)

        try:
            self.storage_manager.update_batch(records=data_to_store, async_update=True)
        except Exception as e:
            bt.logging.error(f"Failed to queue miner commit data for storage: {e}")

    # MARK: Helper Methods
    def get_revealed_commits(self, miner_submissions: dict[int, dict[str, list[dict]]]) -> dict[str, tuple[list[str], list[int]]]:
        """
        Get revealed commits from miner submissions.

        Args:
            miner_submissions: Have same structure as dict returned by get_unscored_miner_submissions() or self.daily_miner_submissions

        Returns:
            dict: {
                challenge_name: ([docker_hub_ids], [miner_uids])
            }
        """
        revealed_commits = {}

        for miner_uid, challenges in miner_submissions.items():
            for challenge_name, submission_data in challenges.items():
                # Handle both single submission and list of submissions
                submissions = submission_data if isinstance(submission_data, list) else [submission_data]

                for submission in submissions:
                    if submission.get("commit"):
                        this_challenge_revealed_commits = revealed_commits.setdefault(
                            challenge_name, ([], [])
                        )
                        docker_hub_id = submission["commit"].split("---")[1]
                        this_challenge_revealed_commits[0].append(docker_hub_id)
                        this_challenge_revealed_commits[1].append(miner_uid)

        return revealed_commits

    def get_unscored_miner_submissions(self) -> dict[int, dict[str, list[dict]]]:
        """
        Filter out submissions that haven't been scored yet from validators_miner_submit.
        For duplicate submissions (same encrypted_commit), keep the one with latest commit_timestamp
        but preserve other fields.

        Returns:
            dict: {
                miner_uid: {
                    challenge_name: [
                        {
                            "commit_timestamp": float,
                            "encrypted_commit": str,
                            "key": str,
                            "commit": str
                        },
                        ...  # unique by encrypted_commit
                    ]
                }
            }
        """
        # Temporary structure to track unique submissions
        temp_submissions = {}

        for validator_uid, miner_submissions in self.validators_miner_submit.items():
            for miner_uid, challenges in miner_submissions.items():
                for challenge_name, submission in challenges.items():
                    if challenge_name not in self.active_challenges:
                        continue

                    if not submission.get("encrypted_commit"):
                        continue

                    # TODO: SHOULD WE RENEW "LOG" FIELD ?
                    # Remove log field to rely only on cache for scoring check
                    submission_copy = {k: v for k, v in submission.items() if k != "log"}
                    submission_copy["log"] = {}

                    if not self._is_submission_scored(challenge_name, submission_copy):
                        temp_submissions.setdefault(miner_uid, {}).setdefault(challenge_name, {})

                        encrypted_commit = submission["encrypted_commit"]
                        existing = temp_submissions[miner_uid][challenge_name].get(encrypted_commit)

                        if existing:
                            # Update timestamp if newer
                            if submission["commit_timestamp"] > existing["commit_timestamp"]:
                                existing["commit_timestamp"] = submission["commit_timestamp"]

                            # Update other fields if they become available
                            for field in ["commit", "key"]:
                                if not existing.get(field) and submission.get(field):
                                    existing[field] = submission[field]
                        else:
                            # Add new submission
                            temp_submissions[miner_uid][challenge_name][encrypted_commit] = submission_copy

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
        hashed_cache_key = self.storage_manager.hash_cache_key(submission["encrypted_commit"])
        cache = self.storage_manager._get_cache(challenge_name)
        cached_submission = cache.get(hashed_cache_key)

        return bool(cached_submission and cached_submission.get("log"))

    # MARK: Endpoints
    class ScoringLogsRequest(BaseModel):
        """
        Inner class to define the body of the POST request for `get_scoring_logs`.
        """
        challenge_name: str
        docker_hub_ids: list[str]

    async def get_scoring_logs(self, scoring_log_request: ScoringLogsRequest) -> dict[str, Optional[list[dict]]]:
        """
        API endpoint to get scoring logs for specific docker hub IDs.

        Args:
            docker_hub_ids: List of docker hub IDs to look up

        Returns:
            dict: {
                docker_hub_id: scoring_log or None if not found
            }
        """
        challenge_name = scoring_log_request.challenge_name
        docker_hub_ids = scoring_log_request.docker_hub_ids

        result = {}
        docker_score_cache = self.storage_manager._get_cache("_docker_hub_id_score_log")

        for docker_id in docker_hub_ids:
            cached_log = docker_score_cache.get(f"{challenge_name}---{docker_id}")
            result[docker_id] = cached_log if cached_log else None

        return result

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