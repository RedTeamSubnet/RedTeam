from fastapi import FastAPI
import uvicorn
from redteam_core import (
    challenge_pool,
    constants,
)
from redteam_core.validator.miner_manager import (
    ChallengeRecord,
    MinerManager,
    ScoringLog
)
from redteam_core.validator.storage_manager import StorageManager
from cryptography.fernet import Fernet
import requests
import argparse
import threading
import time
import copy
import datetime
import bittensor as bt
import os

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=10001)
    parser.add_argument("--netuid", type=int, default=61)
    parser.add_argument("--network", type=str, default="finney")
    parser.add_argument("--reward_app_key", type=str, default=os.getenv("REWARD_APP_KEY"))
    parser.add_argument("--cache_dir", type=str, default="cache_reward_app")
    parser.add_argument("--hf_repo_id", type=str, default=os.getenv("HF_REPO_ID"))
    parser.add_argument("--reward_app_ss58", type=str, default=os.getenv("REWARD_APP_SS58"))
    args = parser.parse_args()
    return args

class RewardApp:
    def __init__(self, args):
        self.args = args
        self.REWARD_APP_KEY = args.reward_app_key
        self.REWARD_APP_SERVER_SS58_ADDRESS = args.reward_app_ss58
        self.REWARD_APP_SERVER_UID = -1
        # self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.miner_managers = {}
        self.smooth_transition_challenge()
        self._init_challenge_records_from_subnet()
        self.subtensor = bt.subtensor(network=args.network)
        self.metagraph = self.subtensor.metagraph(args.netuid, lite=True)
        self.submission_scoring_logs = self.fetch_submission_scoring_logs(list(self.active_challenges.keys()))
        self.previous_submission_scoring_logs = copy.deepcopy(self.submission_scoring_logs)

        self.is_scoring_done = {
            challenge_name: False for challenge_name in self.active_challenges.keys()
        }
        self.miner_submit = {}
        self.mapping_docker_id_miner_id = {}
        self.scoring_dates: list[str] = []

        self.storage_manager = StorageManager(
            cache_dir=self.args.cache_dir,
            hf_repo_id=self.args.hf_repo_id,
            sync_on_init=False
        )

        self.sync_metagraph_thread = threading.Thread(target=self._sync_metagraph, daemon=True).start()
        self.scoring_thread = threading.Thread(target=self.reward_submission, daemon=True).start()
        self.finalize_challenge_result_thread = threading.Thread(target=self.get_challenge_result_of_today, daemon=True).start()

        self.app = FastAPI()
        self.app.add_api_route("/get_scoring_logs", self.get_scoring_logs, methods=["GET"])

    def smooth_transition_challenge(self):
        # TODO: Remove this next update
        """
        Smooth transition challenge from old to new challenge
        """
        all_challenges = challenge_pool.ACTIVE_CHALLENGES
        if datetime.datetime.now(datetime.timezone.utc) <= datetime.datetime(2025, 1, 15, 14, 0, 0, 0, datetime.timezone.utc):
            all_challenges.pop("response_quality_adversarial_v2", None)
            all_challenges.pop("response_quality_ranker_v2", None)
            all_challenges.pop("webui_auto", None)
        else:
            all_challenges.pop("response_quality_adversarial", None)
            all_challenges.pop("response_quality_ranker", None)

        self.active_challenges = all_challenges

        for challenge in self.active_challenges.keys():
            if challenge not in self.miner_managers:
                self.miner_managers[challenge] = MinerManager(challenge_name=challenge, challenge_incentive_weight=self.active_challenges[challenge]["challenge_incentive_weight"])

    def reward_submission(self):
        """Background thread to reward submission.
        1. Fetch miner submit
        2. Group miner submit by challenge
        3. Run challenges
        4. Save submission scoring logs
        5. If no new submission, sleep for 60 seconds
        """
        while True:
            self.smooth_transition_challenge()
            self.fetch_miner_submit(validator_ss58_address=None)
            grouped_miner_submit, self.mapping_docker_id_miner_id = self.group_miner_submit_by_challenge(self.miner_submit)
            self.run_challenges(grouped_miner_submit)
            is_updated = self.save_submission_scoring_logs()
            if not is_updated:
                print("[INFO] No new submission, sleeping for 60 seconds")
                time.sleep(60)

    def get_challenge_result_of_today(self):
        while True:
            today = datetime.datetime.now(datetime.timezone.utc)
            today_key = today.strftime("%Y-%m-%d")
            current_hour = today.hour
            validate_scoring_hour = current_hour >= constants.SCORING_HOUR
            validate_scoring_date = today_key not in self.scoring_dates
            # Validate if scoring is due
            if validate_scoring_hour and validate_scoring_date:
                for challenge_name in self.miner_managers:
                    if self.is_scoring_done.get(challenge_name, False):
                        scoring_logs = []
                        submission_scoring_logs = self.submission_scoring_logs[challenge_name]
                        for docker_hub_id, logs in submission_scoring_logs.items():
                            for log in logs:
                                scoring_logs.append(
                                    ScoringLog(
                                        uid=self.mapping_docker_id_miner_id[docker_hub_id]["uid"], # TODO: Change to log["uid"] in next update
                                        score=log["score"],
                                        miner_input=log.get("miner_input"),
                                        miner_output=log.get("miner_output"),
                                        miner_docker_image=docker_hub_id,
                                        error=log.get("error"),
                                        baseline_score=log.get("baseline_score")
                                    )
                                )
                        self.miner_managers[challenge_name].update_scores(scoring_logs)
                        self._store_challenge_records()
                        bt.logging.info(f"[SCORING] Scoring for challenge: {challenge_name} has been completed for {today_key}")

            if all(self.is_scoring_done.get(challenge_name, False) for challenge_name in self.active_challenges.keys()):
                bt.logging.info(f"[SCORING] All tasks: Scoring completed for {today_key}")
                self.scoring_dates.append(today_key)
            time.sleep(600)


    def run_challenges(self, docker_images_by_challenge: dict):

        for challenge_name, challenge_info in self.active_challenges.items():
            if challenge_name not in self.submission_scoring_logs:
                self.submission_scoring_logs[challenge_name] = {}
            not_scored_submissions = [docker_hub_id for docker_hub_id in docker_images_by_challenge.get(challenge_name, []) if docker_hub_id not in self.submission_scoring_logs.get(challenge_name)]
            not_scored_submissions = list(set(not_scored_submissions))
            not_scored_uids = [self.mapping_docker_id_miner_id[docker_hub_id]["uid"] for docker_hub_id in not_scored_submissions]
            if len(not_scored_submissions) == 0:
                self.is_scoring_done[challenge_name] = True
                continue
            else:
                self.is_scoring_done[challenge_name] = False
            controller = challenge_info["controller"](
                challenge_name=challenge_name,
                miner_docker_images=not_scored_submissions,
                uids=not_scored_uids,
                challenge_info=challenge_info
            )
            logs = controller.start_challenge()
            for log in logs:
                miner_docker_image = log["miner_docker_image"]
                if miner_docker_image not in self.submission_scoring_logs[challenge_name]:
                    self.submission_scoring_logs[challenge_name][miner_docker_image] = []
                self.submission_scoring_logs[challenge_name][miner_docker_image].append(log)

    def group_miner_submit_by_challenge(self, miner_submit: dict):
        docker_images_by_challenge = {}
        mapping_docker_id_miner_id = {}
        for miner_address, challenges in miner_submit.items():
            for challenge_name, commit_data in challenges.items():
                if challenge_name not in self.active_challenges:
                    continue
                if challenge_name not in docker_images_by_challenge:
                    docker_images_by_challenge[challenge_name] = []
                try:
                    if "docker_hub_id" in commit_data:
                        docker_hub_id = commit_data["docker_hub_id"]
                    elif not commit_data.get("commit") and commit_data.get("key") and time.time() - commit_data["commit_timestamp"] > 24 * 60 * 60:
                        f = Fernet(commit_data["key"])
                        commit = f.decrypt(commit_data["encrypted_commit"]).decode()
                        docker_hub_id = commit.split("---")[1]
                    else:
                        docker_hub_id = commit_data["commit"].split("---")[1]

                    current_submit = mapping_docker_id_miner_id.get(docker_hub_id, {})
                    # If current mapping is not exist or current mapping is exist but new commit timestamp is older than current commit timestamp, update mapping"""
                    if not current_submit or (current_submit and current_submit["commit_timestamp"] > commit_data["commit_timestamp"]):
                        mapping_docker_id_miner_id[docker_hub_id] = {
                            "uid": commit_data["uid"],
                            "commit_timestamp": commit_data["commit_timestamp"]
                        }
                    docker_images_by_challenge[challenge_name].append(docker_hub_id)
                except Exception as e:
                    print(f"[ERROR] Error getting docker hub id: {e}")
        return docker_images_by_challenge, mapping_docker_id_miner_id

    def fetch_miner_submit(self, validator_ss58_address: str):
        try:
            endpoint = constants.STORAGE_URL + "/fetch-miner-submit"
            data = {
                "validator_ss58_address": validator_ss58_address,
                "challenge_names": list(self.active_challenges.keys())
            }
            response = requests.post(endpoint, json=data)

            if response.status_code == 200:
                data = response.json()

                for address, challenges in data["miner_submit"].items():
                    if address in self.metagraph.hotkeys:
                        uid = self.metagraph.hotkeys.index(address)
                    else:
                        # Skip if miner hotkey no longer in metagraph
                        continue
                    for challenge_name, commit_data in challenges.items():
                        self.miner_submit.setdefault(address, {})[challenge_name] = {
                            "commit_timestamp": commit_data["commit_timestamp"],
                            "encrypted_commit": commit_data["encrypted_commit"],
                            "key": commit_data["key"],
                            "commit": commit_data["commit"],
                            "uid": uid
                        }

                print("[SUCCESS] Fetched miner submit data from storage.")
            else:
                print(f"[ERROR] Failed to fetch miner submit data: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] Error fetching miner submit data from storage: {e}")

    def fetch_submission_scoring_logs(self, challenge_names: list):
        endpoint = constants.STORAGE_URL + "/fetch-centralized-score"

        submission_scoring_logs = {}
        try:
            response = requests.post(endpoint, json={"challenge_names": challenge_names})
            if response.status_code == 200:
                print("[SUCCESS] Submission scoring logs successfully fetched from storage.")
                logs = response.json()["data"]
                for log in logs:
                    challenge_name = log["challenge_name"]
                    docker_hub_id = log["docker_hub_id"]
                    if challenge_name not in submission_scoring_logs:
                        submission_scoring_logs[challenge_name] = {}
                    submission_scoring_logs[challenge_name][docker_hub_id] = log["logs"]
            else:
                print(f"[ERROR] Failed to fetch submission scoring logs from storage: {response.status_code} - {response.text}")
            return submission_scoring_logs
        except Exception as e:
            print(f"[ERROR] Error fetching submission scoring logs from storage: {e}")
            return {}

    def save_submission_scoring_logs(self):
        endpoint = constants.STORAGE_URL + "/upload-centralized-score"
        try:
            # If all submission scoring logs are empty, return False
            if all(not value for value in self.submission_scoring_logs.values()):
                return False
            # If submission scoring logs are not updated, return False
            if self.previous_submission_scoring_logs == self.submission_scoring_logs:
                return False
            response = requests.post(endpoint, json={"data": self.submission_scoring_logs})
            if response.status_code == 200:
                print("[SUCCESS] Submission scoring logs successfully saved to storage.")
                self.previous_submission_scoring_logs = copy.deepcopy(self.submission_scoring_logs)
            else:
                print(f"[ERROR] Failed to save submission scoring logs to storage: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] Error saving submission scoring logs to storage: {e}")
        return True

    def get_scoring_logs(self, challenge_name: str):
        return {
            "submission_scoring_logs": self.submission_scoring_logs.get(challenge_name, {}),
            "is_scoring_done": self.is_scoring_done.get(challenge_name, False)
        }

    def _sync_metagraph(self, sync_interval= 60 * 10):
        """Background thread to sync metagraph."""
        while True:
            time.sleep(sync_interval)
            try:
                self.metagraph.sync(lite=True)
                bt.logging.success("Metagraph synced successfully.")
            except Exception as e:
                bt.logging.error(f"Error syncing metagraph: {e}")

    def _init_challenge_records_from_subnet(self, is_today_scored: bool = False):
        try:
            endpoint = constants.STORAGE_URL + "/fetch-challenge-records"
            data = {
                "validator_ss58_address": self.REWARD_APP_SERVER_SS58_ADDRESS,
                "is_today_scored": is_today_scored,
                "challenge_names": list(self.active_challenges.keys())
            }
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
            raise  # Re-raise to handle initialization failure

    def _store_challenge_records(self):
        challenge_records = {}
        for challenge_name, miner_manager in self.miner_managers.items():
            challenge_records[challenge_name] =  {
                date: record.__dict__ for date, record in miner_manager.challenge_records.items()
            }
        data = {
            "validator_ss58_address": self.REWARD_APP_SERVER_SS58_ADDRESS,
            "validator_uid": self.REWARD_APP_SERVER_UID,
            "challenge_records": challenge_records,
            "signature": self.REWARD_APP_KEY,
            "nonce": str(time.time_ns())
        }
        self.storage_manager.update_challenge_records(data)
        print("[SUCCESS] Challenge records successfully stored to storage.")


if __name__ == "__main__":
    bt.logging.enable_info()
    args = get_args()
    app = RewardApp(args)

    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=args.port,
    )
