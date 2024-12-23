import time
import json
import datetime
import requests

import numpy as np
import bittensor as bt

from threading import Thread
from cryptography.fernet import Fernet

from redteam_core import (
    Commit,
    BaseValidator,
    challenge_pool,
    constants,
    MinerManager,
    StorageManager,
    ScoringLog,
)
from redteam_core.validator.miner_manager import ChallengeRecord
from redteam_core.common import get_config

class Validator(BaseValidator):
    def __init__(self, config: bt.Config):
        """
        Initializes the Validator by setting up MinerManager instances for all active challenges.
        """
        super().__init__(config)
        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.miner_managers = {
            challenge: MinerManager(challenge_name=challenge, challenge_incentive_weight=self.active_challenges[challenge]["challenge_incentive_weight"])
            for challenge in self.active_challenges.keys()
        }

        # Setup storage manager and publish public hf_repo_id for storage
        self.storage_manager = StorageManager(
            cache_dir=self.config.validator.cache_dir,
            hf_repo_id=self.config.validator.hf_repo_id,
            sync_on_init=True
        )
   
        # Start a thread to periodically commit the repo_id
        commit_thread = Thread(
            target=self.commit_repo_id_to_chain,
            kwargs={"hf_repo_id": self.config.validator.hf_repo_id, "max_retries": 5},
            daemon=True
        )
        commit_thread.start()

        self.miner_submit = self._init_miner_submit_from_cache()
        self.scoring_dates: list[str] = []

    def forward(self):
        self.update_miner_commit(self.active_challenges)
        bt.logging.success(f"[FORWARD] Miner submit: {self.miner_submit}")
        revealed_commits = self.get_revealed_commits()

        self._init_challenge_records_from_subnet(validator_ss58_address=self.metagraph.hotkeys[self.uid])

        for challenge, (commits, uids) in revealed_commits.items():
            if challenge not in self.active_challenges: 
                continue
            self.miner_managers[challenge].update_uid_to_commit(uids=uids, commits=commits)

        if self.config.validator.use_centralized_scoring:
            self.forward_centralized_scoring(revealed_commits)
        else:
            self.forward_local_scoring(revealed_commits)
    
    def _init_miner_submit_from_cache(self):
        miner_submit = {}
        for challenge_name, cache in self.storage_manager.local_caches.items():
            for key in cache:
                submission = cache[key]
                miner_uid = submission["miner_uid"]
                challenge_name = submission["challenge_name"]
                current_submission = miner_submit.setdefault(miner_uid, {}).get(challenge_name)
                if current_submission:
                    current_commit_timestamp = current_submission["commit_timestamp"]
                    # Update submission if it is newer and  encrypted commit is different
                    if current_commit_timestamp < submission["commit_timestamp"] and current_submission["encrypted_commit"] != submission["encrypted_commit"]:
                        miner_submit[miner_uid][challenge_name] = submission
                    # Update submission if it is older and encrypted commit is the same
                    elif current_commit_timestamp > submission["commit_timestamp"] and current_submission["encrypted_commit"] == submission["encrypted_commit"]:
                        miner_submit[miner_uid][challenge_name] = submission
                else:
                    miner_submit[miner_uid][challenge_name] = submission

        return miner_submit

    def forward_centralized_scoring(self, revealed_commits: dict[str, tuple[list[str], list[int]]]): 
        """
        Forward pass for centralized scoring.
        1. Save revealed commits to storage
        2. Get scoring logs from centralized scoring endpoint
        3. Update scores if scoring for all submissions of a challenge is done
        """
        bt.logging.info(f"[FORWARD CENTRALIZED SCORING] Saving Revealed commits to storage ...")
        self.store_miner_commit()
        
        today = datetime.datetime.now()
        today_key = today.strftime("%Y-%m-%d")
        current_hour = today.hour
        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates
        if validate_scoring_hour and validate_scoring_date and revealed_commits:
            is_scoring_done = {
                challenge_name: False for challenge_name in self.active_challenges.keys()
            }
            while True:
                for challenge_name in self.active_challenges.keys():
                    if is_scoring_done[challenge_name]:
                        continue
                    bt.logging.info(f"[FORWARD CENTRALIZED SCORING] Getting scoring logs from centralized scoring endpoint for challenge: {challenge_name} ...")
                    scoring_logs, is_done = self.get_centralized_scoring_logs(challenge_name, revealed_commits)
                    is_scoring_done[challenge_name] = is_done
                    if is_done:
                        bt.logging.info(f"[FORWARD CENTRALIZED SCORING] Scoring done for challenge: {challenge_name} ...")
                        self.miner_managers[challenge_name].update_scores(scoring_logs)
                if all(is_scoring_done.values()):
                    break
                time.sleep(60 * 10)
            
            self.scoring_dates.append(today_key)
            self.store_miner_commit()
            self.store_challenge_records()
        else:
            bt.logging.warning(f"[FORWARD CENTRALIZED SCORING] Skipping scoring for {today_key}")
            bt.logging.info(
                f"[FORWARD CENTRALIZED SCORING] Current hour: {current_hour}, Scoring hour: {constants.SCORING_HOUR}"
            )
            bt.logging.info(f"[FORWARD CENTRALIZED SCORING] Scoring dates: {self.scoring_dates}")
            
    def forward_local_scoring(self, revealed_commits: dict[str, tuple[list[str], list[int]]]):
        """
        Params:
            revealed_commits (dict): A dictionary where the key is the challenge name and the value is a tuple:
                (list of docker_hub_ids, list of uids)
        Executes the forward pass of the Validator: 
        1. Get revealed commits
        2. Validate if scoring is due
        3. Runs challenges and updates scores.
        4. Store the commits.
        """
        today = datetime.datetime.now()
        current_hour = today.hour
        today_key = today.strftime("%Y-%m-%d")
        validate_scoring_hour = current_hour >= constants.SCORING_HOUR
        validate_scoring_date = today_key not in self.scoring_dates
        if validate_scoring_hour and validate_scoring_date and revealed_commits:
            bt.logging.info(f"[FORWARD LOCAL SCORING] Running scoring for {today_key}")
            all_challenge_logs = {}
            for challenge, (commits, uids) in revealed_commits.items():
                if challenge not in self.active_challenges: 
                    continue
                bt.logging.info(f"[FORWARD LOCAL SCORING] Running challenge: {challenge}")
                controller = self.active_challenges[challenge]["controller"](
                    challenge_name=challenge, miner_docker_images=commits, uids=uids, challenge_info=self.active_challenges[challenge]
                )
                logs = controller.start_challenge()
                logs = [ScoringLog(**log) for log in logs]
                all_challenge_logs[challenge] = logs
                self.miner_managers[challenge].update_scores(logs)
                self.store_challenge_records()
                bt.logging.info(f"[FORWARD LOCAL SCORING] Scoring for challenge: {challenge} has been completed for {today_key}")
            bt.logging.info(f"[FORWARD LOCAL SCORING] All tasks: Scoring completed for {today_key}")
            self.scoring_dates.append(today_key)
            self._update_miner_scoring_logs(all_challenge_logs=all_challenge_logs) # Update logs to miner_submit for storing
        else:
            bt.logging.warning(f"[FORWARD LOCAL SCORING] Skipping scoring for {today_key}")
            bt.logging.info(
                f"[FORWARD LOCAL SCORING] Current hour: {current_hour}, Scoring hour: {constants.SCORING_HOUR}"
            )
            bt.logging.info(f"[FORWARD LOCAL SCORING] Scoring dates: {self.scoring_dates}")
            bt.logging.info(
                f"[FORWARD LOCAL SCORING] Revealed commits: {str(revealed_commits)[:100]}..."
            )

        self.store_miner_commit()

    def update_miner_commit(self, active_challenges: dict):
        """
        Queries the axons for miner commit updates and decrypts them if the reveal interval has passed.
        """
         # uids = [1]  # Change this to query multiple uids as needed
        uids = self.metagraph.uids
        axons = [self.metagraph.axons[i] for i in uids]
        dendrite = bt.dendrite(wallet=self.wallet)
        synapse = Commit()

        responses: list[Commit] = dendrite.query(
            axons, synapse, timeout=constants.QUERY_TIMEOUT
        )

        for uid, response in zip(uids, responses):
            this_miner_submit = self.miner_submit.setdefault(uid, {})
            encrypted_commit_dockers = response.encrypted_commit_dockers
            keys = response.public_keys

            for challenge_name, encrypted_commit in encrypted_commit_dockers.items():
                if challenge_name not in active_challenges:
                    this_miner_submit.pop(challenge_name, None)
                    continue
                # Update miner commit data if it's new
                if encrypted_commit != this_miner_submit.get(challenge_name, {}).get(
                    "encrypted_commit"
                ):
                    this_miner_submit[challenge_name] = {
                        "commit_timestamp": time.time(),
                        "encrypted_commit": encrypted_commit,
                        "key": keys.get(challenge_name),
                        "commit": "",
                        "log": {}
                    }

                elif keys.get(challenge_name):
                    this_miner_submit[challenge_name]["key"] = keys.get(challenge_name)

                # Reveal commit if the interval has passed
                commit_timestamp = this_miner_submit[challenge_name]["commit_timestamp"]
                encrypted_commit = this_miner_submit[challenge_name]["encrypted_commit"]
                key = this_miner_submit[challenge_name]["key"]
                if constants.is_commit_on_time(commit_timestamp):
                    try:
                        f = Fernet(key)
                        commit = f.decrypt(encrypted_commit).decode()
                        this_miner_submit[challenge_name]["commit"] = commit
                    except Exception as e:
                        bt.logging.error(f"Failed to decrypt commit: {e}")

    def get_revealed_commits(self) -> dict:
        """
        Collects all revealed commits from miners.

        Returns:
            A dictionary where the key is the challenge name and the value is a tuple:
            (list of docker_hub_ids, list of uids).
        """
        revealed_commits = {}
        for uid, commits in self.miner_submit.items():
            for challenge_name, commit in commits.items():
                bt.logging.info(f"- {uid} - {challenge_name} - {commit}")
                if commit["commit"]:
                    this_challenge_revealed_commits = revealed_commits.setdefault(
                        challenge_name, ([], [])
                    )
                    docker_hub_id = commit["commit"].split("---")[1]
                    this_challenge_revealed_commits[0].append(docker_hub_id)
                    this_challenge_revealed_commits[1].append(uid)
                    commit["docker_hub_id"] = docker_hub_id
        return revealed_commits
    
    def _update_miner_scoring_logs(self, all_challenge_logs: dict[str, list[ScoringLog]]):
        """
        Updates miner submissions with scoring logs for each challenge.
        This method keeps only the most recent 14 days of scoring logs in memory.

        Args:
            all_challenge_logs (dict): A dictionary of challenge names and lists of `ScoringLog` objects.
        
        Raises:
            KeyError: If a miner UID is not found in `miner_submit`.
        """
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        # Track the cutoff date for the TTL (14 days ago)
        cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
        
        for challenge_name, logs in all_challenge_logs.items():
            for log in logs:
                miner_uid = log.uid
                current_logs = self.miner_submit[miner_uid][challenge_name]["log"]

                # Cutoff old scoring and update latest score
                for log_date in list(current_logs.keys()):
                    if log_date < cutoff_date:
                        del current_logs[log_date]
                if today not in current_logs:
                    current_logs[today] = []
                current_logs[today].append(log.model_dump())
                self.miner_submit[miner_uid][challenge_name]["log"] = current_logs
    
    def store_miner_commit(self):
        """
        Store miner commit to storage.
        """
        data_to_store: list[dict] = []

        for uid, commits in self.miner_submit.items():
            for challenge_name, commit in commits.items():
                miner_uid, validator_uid = uid, self.uid
                miner_ss58_address, validator_ss58_address = self.metagraph.hotkeys[miner_uid], self.metagraph.hotkeys[validator_uid]
                # Construct data
                data = {
                    "miner_uid": int(miner_uid),
                    "miner_ss58_address": miner_ss58_address,
                    "validator_uid": validator_uid,
                    "validator_ss58_address": validator_ss58_address,
                    "challenge_name": challenge_name,
                    "commit_timestamp": commit["commit_timestamp"],
                    "encrypted_commit": commit["encrypted_commit"], 
                    # encrypted_commit implicitly converted to string by FastAPI due to lack of annotation so no decode here
                    "key": commit["key"],
                    "commit": commit["commit"],
                    "log": commit["log"]
                }
                # Sign the submission
                self._sign_with_private_key(data=data)

                data_to_store.append(data)
        try:
            self.storage_manager.update_batch(records=data_to_store, async_update=True)
        except Exception as e:
            bt.logging.error(f"Failed to queue miner commit data for storage: {e}")

    def set_weights(self) -> None:
        """
        Sets the weights of the miners on-chain based on their accumulated scores.
        Accumulates scores from all challenges.
        """
        n_uids = len(self.metagraph.axons)
        uids = list(range(n_uids))
        weights = np.zeros(len(uids))

        # Accumulate scores from all challenges
        for challenge, miner_manager in self.miner_managers.items():
            scores = miner_manager.get_onchain_scores(n_uids)
            bt.logging.debug(f"[SET WEIGHTS] {challenge} scores: {scores}")
            weights += scores * miner_manager.challenge_incentive_weight

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

        print(uint_weights, processed_weights)

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
                "challenge_names": list(self.active_challenges.keys())
            }
            self._sign_with_private_key(data)

            response = requests.post(endpoint, json=data)

            if response.status_code == 200:
                data = response.json()
                
                for miner_ss58_address, challenges in data['miner_submit'].items():
                    if miner_ss58_address in self.metagraph.hotkeys:
                        miner_uid = self.metagraph.hotkeys.index(miner_ss58_address)
                    else:
                        # Skip if miner hotkey no longer in metagraph
                        continue
                    for challenge_name, commit_data in challenges.items():
                        self.miner_submit.setdefault(miner_uid, {})[challenge_name] = {
                            "commit_timestamp": commit_data["commit_timestamp"],
                            "encrypted_commit": commit_data["encrypted_commit"],
                            "key": commit_data["key"],
                            "commit": commit_data["commit"],
                            "log": commit_data.get("log")
                        }

                bt.logging.success("[INIT] Miner submit data successfully initialized from storage.")
            else:
                bt.logging.error(f"[INIT] Failed to fetch miner submit data: {response.status_code} - {response.text}")
        except Exception as e:
            bt.logging.error(f"[INIT] Error initializing miner submit data from storage: {e}")

    def _init_challenge_records_from_subnet(self, validator_ss58_address=None, is_today_scored: bool = False):
        try:
            endpoint = constants.STORAGE_URL + "/fetch-challenge-records"
            data = {
                "validator_ss58_address": validator_ss58_address, 
                "is_today_scored": is_today_scored,
                "challenge_names": list(self.active_challenges.keys())
            }
            self._sign_with_private_key(data)
            response = requests.post(endpoint, json=data)

            if response.status_code == 200:
                data = response.json()
                
                for challenge_name, challenge_record in data.items():
                    if challenge_name in self.miner_managers:
                        self.miner_managers[challenge_name].challenge_records = {date: ChallengeRecord(**record) for date, record in challenge_record.items()}
                bt.logging.success("[INIT] Challenge records data successfully initialized from storage.")
            else:
                bt.logging.error(f"[INIT] Failed to fetch challenge records data: {response.status_code} - {response.text}")
        except Exception as e:
            bt.logging.error(f"[INIT] Error initializing challenge records data from storage: {e}")

    def _sign_with_private_key(self, data: dict):
        """
        Signs JSON-serializable data with the validator's private key, adding "nonce" and "signature" fields.

        Args:
            data (dict): JSON-serializable input.

        Raises:
            ValueError: If data is not serializable.
        """
        keypair = self.wallet.hotkey

        # Ensure data is serializable
        try:
            serialized_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        except TypeError as e:
            raise ValueError(f"Data must be JSON serializable: {e}")
    
        nonce = str(time.time_ns())
        # Calculate validator 's signature
        message = f"{serialized_data}{keypair.ss58_address}{nonce}"
        signature = f"0x{keypair.sign(message).hex()}"

        # Add nonce and signature to the data
        data["nonce"] = nonce
        data["signature"] = signature

    def store_challenge_records(self):
        challenge_records = {}
        for challenge_name, miner_manager in self.miner_managers.items():
            challenge_records[challenge_name] =  {
                date: record.__dict__ for date, record in miner_manager.challenge_records.items()
            }
        data = {
            "validator_ss58_address": self.metagraph.hotkeys[self.uid],
            "validator_uid": self.uid,
            "challenge_records": challenge_records
        }
        self._sign_with_private_key(data)
        self.storage_manager.update_challenge_records(data)

    def store_repo_id(self):
        data = {
            "validator_ss58_address": self.metagraph.hotkeys[self.uid],
            "validator_uid": self.uid,
            "hf_repo_id": self.config.validator.hf_repo_id
        }
        self._sign_with_private_key(data)
        self.storage_manager.update_repo_id(data)

    def get_centralized_scoring_logs(self,  challenge_name: str, revealed_commits: dict[str, tuple[list[str], list[int]]]):
        is_scoring_done = False
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            endpoint = constants.REWARDING_URL + "/get_scoring_logs"
            response = requests.get(endpoint, params={"challenge_name": challenge_name}).json()
            submission_scoring_logs = response["submission_scoring_logs"]
            is_scoring_done = response["is_scoring_done"]
            scoring_logs = []
            mapping_dockerid_miner_id = {}
            docker_ids, miner_uids = revealed_commits.get(challenge_name, ([], []))
            for docker_hub_id, miner_uid in zip(docker_ids, miner_uids):
                mapping_dockerid_miner_id[docker_hub_id] = miner_uid
            for docker_hub_id, logs in submission_scoring_logs.items():
                if docker_hub_id in mapping_dockerid_miner_id:
                    miner_uid = mapping_dockerid_miner_id[docker_hub_id]
                    for log in logs:
                        scoring_logs.append(
                            ScoringLog(
                                uid=miner_uid, 
                                score=log["score"], 
                                miner_input=log["miner_input"], 
                                miner_output=log["miner_output"], 
                                miner_docker_image=docker_hub_id
                            )
                        )
                        self.miner_submit[miner_uid].setdefault(challenge_name, {}).setdefault("log", {}).setdefault(today, []).append(log)

        except Exception as e:
            bt.logging.error(f"[GET CENTRALIZED SCORING LOGS] Error getting scoring logs: {e}")
        return scoring_logs, is_scoring_done

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
        self.store_repo_id()

        for attempt in range(1, max_retries + 1):
            try:
                bt.logging.info(f"Attempting to commit repo ID '{hf_repo_id}' to the blockchain (Attempt {attempt})...")
                self.subtensor.commit(
                    wallet=self.wallet,
                    netuid=self.config.netuid,
                    data=message,
                )
                bt.logging.success(f"Successfully committed repo ID '{hf_repo_id}' to the blockchain.")
                return
            except Exception as e:
                bt.logging.error(f"Error committing repo ID '{hf_repo_id}' on attempt {attempt}: {e}")
                if attempt == max_retries:
                    bt.logging.error(
                        f"Failed to commit repo ID '{hf_repo_id}' to the blockchain after {max_retries} attempts."
                    )
                
    def _commit_repo_id_to_chain_periodically(self, hf_repo_id: str, interval: int) -> None:
        """
        Periodically commits the repository ID to the blockchain.

        Args:
            interval (int): Time interval in seconds between consecutive commits.
        """
        while True:
            try:
                self.commit_repo_id_to_chain(hf_repo_id=hf_repo_id)
                bt.logging.info("Periodic commit HF repo id to chain completed successfully.")
            except Exception as e:
                bt.logging.error(f"Error in periodic commit for repo ID '{self.config.validator.hf_repo_id}': {e}")
            time.sleep(interval)

if __name__ == "__main__":
    with Validator(get_config()) as validator:
        while True:
            bt.logging.info("Validator is running...")
            time.sleep(constants.EPOCH_LENGTH // 4)
