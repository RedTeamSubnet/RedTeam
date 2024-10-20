from scriptcurity_core import (
    Commit,
    BaseValidator,
    challenge_pool,
    constants,
    MinerManager,
    ScoringLog,
)
import bittensor as bt
import time
from cryptography.fernet import Fernet
import numpy as np
import time


class Validator(BaseValidator):
    def __init__(self):
        """
        Initializes the Validator by setting up MinerManager instances for all active challenges.
        """
        super().__init__()
        self.active_challenges = challenge_pool.ACTIVE_CHALLENGES
        self.miner_managers = {
            challenge: MinerManager(challenge_name=challenge)
            for challenge in self.active_challenges.keys()
        }

    def forward(self):
        """
        Executes the forward pass of the Validator:
        1. Updates miner commit information.
        2. Reveals commits.
        3. Runs challenges and updates scores.
        """
        self.update_miner_commit()
        bt.logging.success(f"[FORWARD] Miner submit: {self.miner_submit}")

        revealed_commits = self.get_revealed_commits()
        bt.logging.info(f"[FORWARD] Revealed commits: {revealed_commits}")

        for challenge, (commits, uids) in revealed_commits.items():
            controller = self.active_challenges[challenge](
                challenge_name=challenge, miner_docker_images=commits, uids=uids
            )
            logs = controller.start_challenge()
            logs = [ScoringLog(**log) for log in logs]
            self.miner_managers[challenge].update_scores(logs)

    def update_miner_commit(self):
        """
        Queries the axons for miner commit updates and decrypts them if the reveal interval has passed.
        """
        uids = [0]  # Change this to query multiple uids as needed
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
                # Update miner commit data if it's new
                if encrypted_commit != this_miner_submit.get(challenge_name, {}).get(
                    "encrypted_commit"
                ):
                    this_miner_submit[challenge_name] = {
                        "commit_timestamp": time.time(),
                        "encrypted_commit": encrypted_commit,
                        "key": keys.get(challenge_name),
                        "commit": "",
                    }

                # Reveal commit if the interval has passed
                commit_timestamp = this_miner_submit[challenge_name]["commit_timestamp"]
                encrypted_commit = this_miner_submit[challenge_name]["encrypted_commit"]
                key = this_miner_submit[challenge_name]["key"]
                if time.time() - commit_timestamp > constants.REVEAL_INTERVAL and key:
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
        return revealed_commits

    def update_scores(self, challenge: str, scores: dict) -> None:
        """
        Updates the scores for each miner in a challenge.

        Args:
            challenge: The challenge name.
            scores: A dictionary of miner scores (key: miner, value: score).
        """
        for miner, score in scores.items():
            self.scores.setdefault(miner, []).append(score)
            self.scores[miner] = self.scores[miner][: constants.N_LAST_SCORES]

    def set_weights(self) -> None:
        """
        Sets the weights of the miners on-chain based on their accumulated scores.
        Accumulates scores from all challenges.
        """
        uids = list(range(len(self.metagraph.axons)))
        weights = np.zeros(len(uids))

        # Accumulate scores from all challenges
        for uid, score_list in self.scores.items():
            weights[uid] = sum(score_list) / len(score_list) if score_list else 0

        # Set weights on-chain
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
