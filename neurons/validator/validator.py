import datetime
import json
import time
import traceback
from copy import deepcopy
from typing import Optional, Tuple, Union

import bittensor as bt
import numpy as np
import requests
from cryptography.fernet import Fernet

from redteam_core import BaseValidator, Commit, challenge_pool, constants
from redteam_core.common import get_config
from redteam_core.validator import (
    ChallengeManager,
    # MinerManager,
    ScoringLog,
    StorageManager,
    start_bittensor_log_listener,
)

from redteam_core.validator.miner_manager import MinerManager
from redteam_core.validator.models import MinerChallengeCommit
from redteam_core.validator.utils import create_validator_request_header_fn


class Validator(BaseValidator):
    def __init__(self, config: bt.Config):
        """
        Initializes the Validator by setting up MinerManager instances for all active challenges.
        """
        super().__init__(config)

        # Get the storage API key
        storage_api_key = self._get_storage_api_key()

        # Start the Bittensor log listener
        start_bittensor_log_listener(api_key=storage_api_key)

        # Setup storage manager and publish public hf_repo_id for storage
        self.validator_request_header_fn = create_validator_request_header_fn(
            uid=self.uid,
            hotkey=self.wallet.hotkey.ss58_address,
            keypair=self.wallet.hotkey,
        )
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
        ] = {}  # {(uid, ss58_address): {challenge_name: MinerCommit}}
        self._init_validator_state()

        self.scoring_dates: list[str] = []

    # MARK: Initialization and Setup
    def _init_active_challenges(self):
        # Avoid mutating the original ACTIVE_CHALLENGES
        all_challenges = deepcopy(challenge_pool.ACTIVE_CHALLENGES)

        # Remove challenges that are not active and setup the active challenges
        if datetime.datetime.now(datetime.timezone.utc) <= datetime.datetime(
            2025, 2, 14, 14, 0, 0, 0, datetime.timezone.utc
        ):
            all_challenges.pop("response_quality_adversarial_v3", None)
            all_challenges.pop("response_quality_ranker_v3", None)
            all_challenges.pop("humanize_behaviour_v1", None)
        else:
            all_challenges.pop("response_quality_adversarial_v2", None)
            all_challenges.pop("response_quality_ranker_v2", None)
            all_challenges.pop("webui_auto", None)

        self.active_challenges = all_challenges
        for challenge in self.active_challenges.keys():
            if challenge not in self.challenge_managers:
                self.challenge_managers[challenge] = ChallengeManager(
                    challenge_info=self.active_challenges[challenge],
                    metagraph=self.metagraph,
                )

        self.miner_managers.update_challenge_managers(self.challenge_managers)

    def _init_validator_state(self):
        """
        Initialize validator state based on scoring configuration.

        This method handles initialization of two key components:
        1. Challenge Records: Always initialized from subnet to ensure network consistency
        2. Miner Submissions: Source depends on scoring configuration
            - Centralized scoring: Initialize from subnet
            - Local scoring: Initialize from local cache

        Note: This method should be called during validator initialization
        to ensure proper state setup before processing any challenges.
        """
        bt.logging.info("[INIT] Starting validator state initialization...")

        # Always init challenge records from subnet for network consistency
        self._init_challenge_records_from_subnet()

        # Initialize miner submissions based on scoring mode
        if self.config.validator.use_centralized_scoring:
            self._init_miner_submit_from_subnet()
        else:
            self._init_miner_submit_from_cache()

        bt.logging.success("[INIT] Validator state initialization completed")

    def _init_miner_submit_from_cache(self):
        """
        Initializes miner_submit data from local cache.
        """
        miner_submit = {}
        for challenge_name, cache in self.storage_manager.local_caches.items():
            for key in cache:
                submission = cache[key]
                miner_uid = submission["miner_uid"]
                miner_ss58_address = submission["miner_ss58_address"]
                challenge_name = submission["challenge_name"]
                current_submission = miner_submit.setdefault(
                    (miner_uid, miner_ss58_address), {}
                ).get(challenge_name)
                if current_submission:
                    current_commit_timestamp = current_submission["commit_timestamp"]
                    # Update submission if it is newer and encrypted commit is different
                    if (
                        current_commit_timestamp < submission["commit_timestamp"]
                        and current_submission["encrypted_commit"]
                        != submission["encrypted_commit"]
                    ):
                        miner_submit[(miner_uid, miner_ss58_address)][
                            challenge_name
                        ] = submission
                    # Update submission if it is older and encrypted commit is the same
                    elif (
                        current_commit_timestamp > submission["commit_timestamp"]
                        and current_submission["encrypted_commit"]
                        == submission["encrypted_commit"]
                    ):
                        miner_submit[(miner_uid, miner_ss58_address)][
                            challenge_name
                        ] = submission
                else:
                    miner_submit[(miner_uid, miner_ss58_address)][challenge_name] = (
                        submission
                    )

        self.miner_commits = miner_submit

    def _init_miner_submit_from_subnet(self, is_today_scored: bool = False):
        """
        Initializes miner_submit data from subnet by fetching the data from the API endpoint
        and populating the miner_submit dictionary with the response.
        """
        try:
            endpoint = constants.STORAGE_URL + "/fetch-miner-submit"
            data = {
                "validator_ss58_address": self.metagraph.hotkeys[self.uid],
                "is_today_scored": is_today_scored,
                "challenge_names": list(self.active_challenges.keys()),
            }
            self._sign_with_private_key(data)

            response = requests.post(endpoint, json=data)

            if response.status_code == 200:
                data = response.json()

                for miner_ss58_address, challenges in data["miner_submit"].items():
                    if miner_ss58_address in self.metagraph.hotkeys:
                        miner_uid = self.metagraph.hotkeys.index(miner_ss58_address)
                    else:
                        # Skip if miner hotkey no longer in metagraph
                        continue
                    for challenge_name, commit_data in challenges.items():
                        self.miner_commits.setdefault(
                            (miner_uid, miner_ss58_address), {}
                        )[challenge_name] = {
                            "commit_timestamp": commit_data["commit_timestamp"],
                            "encrypted_commit": commit_data["encrypted_commit"],
                            "key": commit_data["key"],
                            "commit": commit_data["commit"],
                            "log": commit_data.get("log", {}),
                        }

                bt.logging.success(
                    "[INIT] Miner submit data successfully initialized from storage."
                )
            else:
                bt.logging.error(
                    f"[INIT] Failed to fetch miner submit data: {response.status_code} - {response.text}"
                )
        except Exception as e:
            bt.logging.error(
                f"[INIT] Error initializing miner submit data from storage: {e}"
            )

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
        main loop to process new miner submissions and update scores.
        """
        self._init_active_challenges()
        self.update_miner_commits(self.active_challenges)
        bt.logging.success(
            f"[FORWARD] Forwarding for {datetime.datetime.now(datetime.timezone.utc)}"
        )
        revealed_commits = self.get_revealed_commits()

        for challenge, commits in revealed_commits.items():
            if challenge not in self.active_challenges:
                continue
            self.challenge_managers[challenge].update_miner_infos(miner_commits=commits)

        if self.config.validator.use_centralized_scoring:
            self.forward_centralized_scoring(revealed_commits)
        else:
            self.forward_local_scoring(revealed_commits)

        self.store_miner_commits()

    def forward_centralized_scoring(
        self, revealed_commits: dict[str, tuple[list[str], list[Tuple[int, str]]]]
    ):
        """
        Forward pass for centralized scoring.
        1. Save revealed commits to storage
        2. Get scoring logs from centralized scoring endpoint
        3. Update scores if scoring for all submissions of a challenge is done

        Args:
            revealed_commits (dict): Mapping of challenge names to their commit data
                Format: {
                    "challenge_name": ([docker_hub_ids], [(miner_uid, miner_ss58_address) pairs])
                }
        """
        bt.logging.info(
            "[FORWARD CENTRALIZED SCORING] Saving Revealed commits to storage ..."
        )
        self.store_miner_commits()

        # Get current time info
        today = datetime.datetime.now(datetime.timezone.utc)
        today_key = today.strftime("%Y-%m-%d")
        current_hour = today.hour
        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates
        # Validate if scoring is due
        if validate_scoring_hour and validate_scoring_date and revealed_commits:
            # Store logs for all submissions from all challenges
            all_challenge_logs: dict[str, list[ScoringLog]] = {}
            # Initialize a dictionary to track if scoring is done for each challenge
            is_scoring_done = {
                challenge_name: False
                for challenge_name in self.active_challenges.keys()
            }

            # Loop until all challenges have finished scoring
            while True:
                for challenge_name in self.active_challenges.keys():
                    if is_scoring_done[challenge_name]:
                        continue

                    try:
                        bt.logging.info(
                            f"[FORWARD CENTRALIZED SCORING] Getting scoring logs from centralized scoring endpoint for challenge: {challenge_name} ..."
                        )
                        logs, is_done = self.get_centralized_scoring_logs(
                            challenge_name, revealed_commits
                        )
                        is_scoring_done[challenge_name] = is_done

                        if is_done:
                            bt.logging.info(
                                f"[FORWARD CENTRALIZED SCORING] Scoring done for challenge: {challenge_name} ..."
                            )
                            all_challenge_logs[challenge_name] = logs
                            self.miner_managers[challenge_name].update_scores(logs)
                    except Exception as e:
                        # Continue to next challenge if error occurs
                        bt.logging.error(
                            f"[FORWARD CENTRALIZED SCORING] Error getting scoring logs and update scores for challenge: {challenge_name}: {traceback.format_exc()}"
                        )
                        continue

                # Break if all challenges have finished scoring
                if all(is_scoring_done.values()):
                    break
                # TODO: CHECK IF THIS CAN BLOCK INDEFINITELY
                # Sleep for a period before checking again
                time.sleep(60 * 10)

            self.scoring_dates.append(today_key)
            self._update_miner_scoring_logs(
                all_challenge_logs=all_challenge_logs
            )  # Update logs to miner_submit for storing
            self.store_challenge_records()  # n_uidsTODO: REMOVE AFTER TWO WEEKS WHEN ALL VALIDATORS HAVE UPDATED TO NEW VERSION
            self.store_challenge_records_new(
                dates=today_key
            )  # Store challenge records for today
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
            - Check challenge manager and storage manager for comparision inputs
            - Runs the challenge controller on miner's submission with new inputs generated for scoring and comparison
            - Compare miner's output with the unique solutions set
            - Updates scores in challenge manager
        3. Updates all scoring logs and store challenge records after validating

        Args:
            revealed_commits (dict): Mapping of challenge names to the revealed miner commits
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

            for challenge, (
                commits,
                miner_uid_ss58_address_pairs,
            ) in revealed_commits.items():
                if challenge not in self.active_challenges:
                    continue
                # 1. Gather comparision inputs
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
                    unique_commits_cached_data = [
                        MinerChallengeCommit(
                            **challenge_local_cache.get(unique_commit_cache_key)
                        )
                        for unique_commit_cache_key in unique_commits_cache_keys
                    ]

                # 2. Run challenge controller
                bt.logging.info(
                    f"[FORWARD LOCAL SCORING] Running challenge: {challenge}"
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
                comparer = self.active_challenges[challenge]["comparer"](
                    challenge_name=challenge,
                    challenge_info=self.active_challenges[challenge],
                    miner_commits=commits,
                )
                # Run comparision, the comparer update commit 's penalty and comparison logs directly
                comparer.start_comparision()

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

    def get_centralized_scoring_logs(
        self,
        challenge_name: str,
        revealed_commits: dict[str, tuple[list[str], list[int]]],
    ) -> tuple[list[ScoringLog], bool]:
        """
        Get scoring logs from centralized server and determine if scoring is complete for all revealed commits.

        Args:
            challenge_name: Name of the challenge
            revealed_commits: Dictionary mapping challenge names to tuples of (docker_ids, miner_uids)

        Returns:
            tuple: (scoring_logs, is_scoring_done)
                - scoring_logs: List of ScoringLog objects
                - is_scoring_done: True if all revealed commits have scores
        """
        scoring_logs = []

        try:
            # Get revealed docker IDs for this challenge
            docker_ids, miner_uids = revealed_commits.get(challenge_name, ([], []))
            if not docker_ids:  # No commits to score
                return scoring_logs, True

            # Create mapping of docker_id to miner_uid
            mapping_docker_id_miner_id = dict(zip(docker_ids, miner_uids))

            # Get scoring logs from server
            endpoint = constants.REWARDING_URL + "/get_scoring_logs"
            endpoint_v2 = constants.REWARDING_URL + "/v2/get_scoring_logs"

            # Try new API first
            try:
                response = requests.get(
                    endpoint_v2,
                    params={
                        "challenge_name": challenge_name,
                        "docker_hub_ids": docker_ids,
                    },
                )
                response.raise_for_status()
                submission_scoring_logs: dict[str, Optional[list[dict]]] = (
                    response.json()
                )
                # Track which docker IDs have scores
                scored_docker_ids = set()

                # Process scoring logs
                for docker_hub_id, logs in submission_scoring_logs.items():
                    try:
                        if docker_hub_id in mapping_docker_id_miner_id and logs:
                            miner_uid = mapping_docker_id_miner_id[docker_hub_id]
                            scored_docker_ids.add(docker_hub_id)

                            for log in logs:
                                scoring_logs.append(
                                    ScoringLog(
                                        uid=miner_uid,
                                        score=log["score"],
                                        miner_input=log["miner_input"],
                                        miner_output=log["miner_output"],
                                        miner_docker_image=docker_hub_id,
                                        error=log.get("error"),
                                        baseline_score=log.get("baseline_score"),
                                    )
                                )
                    except Exception as e:
                        bt.logging.error(
                            f"[GET CENTRALIZED SCORING LOGS] Get scoring logs for{docker_hub_id} failed: {e}"
                        )
            except (requests.RequestException, KeyError):
                # TODO: OLD VERSION, REMOVE AFTER TWO WEEKS WHEN ALL VALIDATORS HAVE UPDATED TO NEW VERSION
                # Fallback to old API format
                bt.logging.warning(
                    f"[GET CENTRALIZED SCORING LOGS] Falling back to old API format for challenge: {challenge_name}"
                )
                response = requests.get(
                    endpoint, params={"challenge_name": challenge_name}
                )
                response.raise_for_status()
                data = response.json()

                submission_scoring_logs = data["submission_scoring_logs"]

                # Track which docker IDs have scores
                scored_docker_ids = set()

                # Process scoring logs
                for docker_hub_id, logs in submission_scoring_logs.items():
                    try:
                        if docker_hub_id in mapping_docker_id_miner_id and logs:
                            miner_uid = mapping_docker_id_miner_id[docker_hub_id]
                            scored_docker_ids.add(docker_hub_id)

                            for log in logs:
                                scoring_logs.append(
                                    ScoringLog(
                                        uid=miner_uid,
                                        score=log["score"],
                                        miner_input=log.get("miner_input"),
                                        miner_output=log.get("miner_output"),
                                        miner_docker_image=docker_hub_id,
                                        error=log.get("error"),
                                        baseline_score=log.get("baseline_score"),
                                    )
                                )
                    except Exception as e:
                        bt.logging.error(
                            f"[GET CENTRALIZED SCORING LOGS] Get scoring logs for{docker_hub_id} failed: {e}"
                        )
            # Determine if scoring is complete by checking if all revealed commits have scores
            is_scoring_done = len(scored_docker_ids) == len(
                set(docker_ids)
            ) or data.get("is_scoring_done", False)

        except Exception as e:
            bt.logging.error(
                f"[GET CENTRALIZED SCORING LOGS] Error getting scoring logs: {e}"
            )
            return scoring_logs, False

        return scoring_logs, is_scoring_done

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

        bt.logging.info(f"[SET WEIGHTS] uint_weights: {uint_weights}, processed_weights: {processed_weights}")

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
        # uids = [1]  # Change this to query multiple uids as needed
        uids = self.metagraph.uids

        axons = [self.metagraph.axons[i] for i in uids]
        ss58_addresses = [self.metagraph.hotkeys[i] for i in uids]
        dendrite = bt.dendrite(wallet=self.wallet)
        synapse = Commit()

        responses: list[Commit] = dendrite.query(
            axons, synapse, timeout=constants.QUERY_TIMEOUT
        )

        # Update new miner commits to self.miner_commits
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
                # Update miner commit data if it's new
                if encrypted_commit != current_miner_commit.encrypted_commit:
                    current_miner_commit.commit_timestamp = time.time()
                    current_miner_commit.encrypted_commit = encrypted_commit
                    current_miner_commit.key = keys.get(challenge_name)
                    current_miner_commit.commit = ""
                    current_miner_commit.scoring_logs = []

                elif keys.get(challenge_name):
                    current_miner_commit.key = keys.get(challenge_name)

                # Reveal commit if the interval has passed
                commit_timestamp = current_miner_commit.commit_timestamp
                encrypted_commit = current_miner_commit.encrypted_commit
                key = current_miner_commit.key
                if key and constants.is_commit_on_time(commit_timestamp):
                    try:
                        f = Fernet(key)
                        commit = f.decrypt(encrypted_commit).decode()
                        current_miner_commit.commit = commit
                    except Exception as e:
                        bt.logging.error(f"Failed to decrypt commit: {e}")

        # Cutoff miners not in metagraph using dict comprehension
        self.miner_commits = {
            (uid, ss58_address): commits
            for (uid, ss58_address), commits in self.miner_commits.items()
            if ss58_address in self.metagraph.hotkeys
        }

    def get_revealed_commits(self) -> dict[str, list[MinerChallengeCommit]]:
        """
        Collects all revealed commits from miners.
        This method make sure docker_hub_id is unique for each challenge, only one commit of same docker_hub_id will be returned for each challenge.

        Returns:
            A dictionary where the key is the challenge name and the value is a tuple:
            (list of docker_hub_ids, list of (uid, hotkey) pairs).
        """
        docker_hub_ids = {}
        revealed_commits: dict[str, list[MinerChallengeCommit]] = {}
        for (uid, ss58_address), commits in self.miner_commits.items():
            for challenge_name, commit in commits.items():
                bt.logging.info(
                    f"- {uid} - {ss58_address} - {challenge_name} - {commit.encrypted_commit}"
                )
                if commit.commit:
                    this_challenge_revealed_commits = revealed_commits.setdefault(
                        challenge_name, []
                    )
                    docker_hub_id = commit.commit.split("---")[1]
                    commit.docker_hub_id = docker_hub_id

                    # Make sure docker_hub_id is unique for each challenge
                    this_challenge_docker_hub_ids = docker_hub_ids.setdefault(
                        challenge_name, set()
                    )
                    if docker_hub_id not in this_challenge_docker_hub_ids:
                        this_challenge_revealed_commits.append(commit)
                        this_challenge_docker_hub_ids.add(docker_hub_id)

        return revealed_commits

    # MARK: Storage
    def store_miner_commits(self):
        """
        Store miner commita to storage.
        """
        data_to_store: list[MinerChallengeCommit] = [
            commit
            for (uid, ss58_address), commits in self.miner_commits.items()
            for challenge_name, commit in commits.items()
        ]

        try:
            self.storage_manager.update_batch(
                records=data_to_store, process_method="update_commit", async_update=True
            )
        except Exception as e:
            bt.logging.error(f"Failed to queue miner commit data for storage: {e}")

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
        endpoint = f"{constants.STORAGE_URL}/api-key"
        data = {
            "validator_uid": self.uid,
            "validator_ss58_address": self.metagraph.hotkeys[self.uid],
        }
        self._sign_with_private_key(data)
        response = requests.post(endpoint, json=data)
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


if __name__ == "__main__":
    with Validator(get_config()) as validator:
        while True:
            bt.logging.info("Validator is running...")
            time.sleep(constants.EPOCH_LENGTH // 4)
