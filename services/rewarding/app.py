from fastapi import FastAPI
import uvicorn
from redteam_core import (
    challenge_pool,
    constants,
)
import requests
import argparse
import threading
import time
import copy
import bittensor as bt

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=47920)
    parser.add_argument("--netuid", type=int, default=61)
    parser.add_argument("--network", type=str, default="finney")
    args = parser.parse_args()
    return args

class RewardApp:
    def __init__(self, args):
        self.args = args
        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.subtensor = bt.subtensor(network=args.network)
        self.metagraph = self.subtensor.metagraph(args.netuid, lite=True)
        self.submission_scoring_logs = self.fetch_submission_scoring_logs(list(self.active_challenges.keys()))
        self.previous_submission_scoring_logs = copy.deepcopy(self.submission_scoring_logs)

        self.is_scoring_done = {
            challenge_name: False for challenge_name in self.active_challenges.keys()
        }
        self.sync_metagraph_thread = threading.Thread(target=self._sync_metagraph, daemon=True).start()
        self.scoring_thread = threading.Thread(target=self.reward_submission, daemon=True).start()
        self.miner_submit = {}

        self.app = FastAPI()
        self.app.add_api_route("/get_scoring_logs", self.get_scoring_logs, methods=["GET"])
        
        

    def reward_submission(self):
        """Background thread to reward submission.
        1. Fetch miner submit
        2. Group miner submit by challenge
        3. Run challenges
        4. Save submission scoring logs
        5. If no new submission, sleep for 60 seconds
        """
        while True:
            self.fetch_miner_submit(validator_ss58_address=None)
            grouped_miner_submit = self.group_miner_submit_by_challenge(self.miner_submit)
            self.run_challenges(grouped_miner_submit)
            is_updated = self.save_submission_scoring_logs()
            if not is_updated:
                print("[INFO] No new submission, sleeping for 60 seconds")
                time.sleep(60)
    
    def run_challenges(self, docker_images_by_challenge: dict):

        for challenge_name, challenge_info in self.active_challenges.items():
            if challenge_name not in self.submission_scoring_logs:
                self.submission_scoring_logs[challenge_name] = {}
            not_scored_submissions = [docker_hub_id for docker_hub_id in docker_images_by_challenge.get(challenge_name, []) if docker_hub_id not in self.submission_scoring_logs.get(challenge_name)]
            not_scored_submissions = list(set(not_scored_submissions))
            if len(not_scored_submissions) == 0:
                self.is_scoring_done[challenge_name] = True
                continue
            else:
                self.is_scoring_done[challenge_name] = False
            controller = challenge_info["controller"](
                challenge_name=challenge_name, 
                miner_docker_images=not_scored_submissions, 
                uids=range(len(not_scored_submissions)), # not used
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
        for miner_address, challenges in miner_submit.items():
            for challenge_name, commit_data in challenges.items():
                if challenge_name not in self.active_challenges:
                    continue
                if challenge_name not in docker_images_by_challenge:
                    docker_images_by_challenge[challenge_name] = []
                try:
                    if "docker_hub_id" in commit_data:
                        docker_hub_id = commit_data["docker_hub_id"]
                    else:
                        docker_hub_id = commit_data["commit"].split("---")[1]
                    docker_images_by_challenge[challenge_name].append(docker_hub_id)
                except Exception as e:
                    print(f"[ERROR] Error getting docker hub id: {e}")                
        return docker_images_by_challenge

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
                
                for address, challenges in data['miner_submit'].items():
                    if address  in self.metagraph.hotkeys:
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

if __name__ == "__main__":
    bt.logging.enable_info()
    args = get_args()
    app = RewardApp(args)

    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=args.port,
    )
