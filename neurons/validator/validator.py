from scriptcurity_core import Commit, BaseValidator, challenges, constants
import bittensor as bt
import time
from cryptography.fernet import Fernet
import numpy as np


class Validator(BaseValidator):
    def __init__(self):
        super().__init__()
        self.active_challenges = challenges.ACTIVE_CHALLENGES
        self.miner_submit = {}
        self.scores = {}

    def forward(self):
        self.update_miner_submit()
        revealed_commits = self.get_revealed_commits()
        bt.logging.info(f"Revealed commits: {revealed_commits}")
        for challenge, (commits, uids) in revealed_commits.items():
            controller = self.active_challenges[challenge](
                challenge_name=challenge, miner_docker_images=commits, uids=uids
            )
            miner_scores, logs = controller.start_challenge()

            self.update_scores(miner_scores)

    def update_miner_submit(self):
        uids = list(range(len(self.metagraph.axons)))
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
                if encrypted_commit != this_miner_submit.get(challenge_name, {}).get(
                    "encrypted_commit"
                ):
                    this_miner_submit[challenge_name] = {
                        "commit_timestamp": time.time(),
                        "encrypted_commit": encrypted_commit,
                        "key": keys.get(challenge_name),
                        "commit": "",
                    }
                commit_timestamp = this_miner_submit[challenge_name]["commit_timestamp"]
                encrypted_commit = this_miner_submit[challenge_name]["encrypted_commit"]
                key = this_miner_submit[challenge_name]["key"]
                if time.time() - commit_timestamp > constants.REVEAL_INTERVAL and key:
                    f = Fernet(key)
                    commit = f.decrypt(encrypted_commit).decode()
                    this_miner_submit[challenge_name]["commit"] = commit

    def get_revealed_commits(self):
        revealed_commits = {}
        for uid, commits in self.miner_submit.items():
            for challenge_name, commit in commits.items():
                if commit["commit"]:
                    this_challenge_revealed_commits = revealed_commits.setdefault(
                        challenge_name, ([], [])
                    )
                    this_challenge_revealed_commits[0].append(commit["commit"])
                    this_challenge_revealed_commits[1].append(uid)
        return revealed_commits

    def update_scores(self, scores):
        for miner, score in scores.items():
            self.scores.setdefault(miner, []).append(score)
            self.scores[miner] = self.scores[miner][: constants.N_LAST_SCORES]

    def set_weights(self):
        uids = list(range(len(self.metagraph.axons)))
        weights = np.zeros(len(uids))
        for uid, score_list in self.scores.items():
            weights[uid] = sum(score_list) / len(score_list)

        result, log = self.subtensor.set_weights(
            wallet=self.wallet,
            netuid=self.config.netuid,
            uids=uids,
            weights=weights,
            version_key=constants.__spec_version__,
        )
        if result:
            bt.logging.success(f"[SET WEIGHTS]: {log}")
        else:
            bt.logging.error(f"[SET WEIGHTS]: {log}")


if __name__ == "__main__":
    validator = Validator()
    validator.synthetic_loop_in_background_thread()
