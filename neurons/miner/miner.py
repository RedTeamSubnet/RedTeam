from scriptcurity_core import BaseMiner, Commit, constants
from typing import Tuple
import bittensor as bt
import time
import json
import yaml
import os


class Miner(BaseMiner):
    def __init__(self):
        super().__init__()
        self.synapse_commit = self._load_synapse_commit()

    def forward(self, synapse: Commit) -> Commit:
        active_commits = self._load_active_commit()
        served_commits = list(self.synapse_commit.commit_dockers.keys())
        for commit in active_commits:
            if commit not in served_commits:
                self.synapse_commit.add_encrypted_commit(commit)
        bt.logging.info(f"Synapse commit: {self.synapse_commit}")
        self.synapse_commit.reveal_if_ready()
        return self.synapse_commit

    def blacklist(self, synapse: Commit) -> Tuple[bool, str]:
        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        stake = self.metagraph.S[uid]
        if stake < constants.MIN_VALIDATOR_STAKE:
            return True, "Not enough stake"
        return False, "Passed"

    def _load_synapse_commit(self) -> Commit:
        commit_file = self.config.neuron.fullpath + "/commit.json"
        if not os.path.exists(commit_file):
            return Commit()
        commit = json.load(open(commit_file))
        commit = Commit(**commit)
        return commit

    def _save_synapse_commit(self):
        commit_file = self.config.neuron.fullpath + "/commit.json"
        json.dump(self.synapse_commit, open(commit_file, "w"))

    def _load_active_commit(self) -> list:
        commit_file = "neurons/miner/active_commit.yaml"
        commit = yaml.load(open(commit_file), yaml.FullLoader)
        return commit


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info("Miner is running.")
            time.sleep(10)
