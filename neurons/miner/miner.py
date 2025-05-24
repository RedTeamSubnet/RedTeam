#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import yaml
import pickle
from typing import Tuple

import bittensor as bt

from redteam_core import BaseMiner, Commit, constants


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
        self._save_synapse_commit()
        synapse_response = self.synapse_commit._hide_secret_info()
        return synapse_response

    def blacklist(self, synapse: Commit) -> Tuple[bool, str]:
        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        stake = self.metagraph.S[uid]
        if stake < constants.MIN_VALIDATOR_STAKE:
            return True, "Not enough stake"
        return False, "Passed"

    def _load_synapse_commit(self) -> Commit:
        commit_file = self.config.neuron.fullpath + "/commit.pkl"
        if not os.path.exists(commit_file):
            return Commit()
        with open(commit_file, "rb") as f:
            commit = pickle.load(f)
        return commit

    def _save_synapse_commit(self):
        commit_file = self.config.neuron.fullpath + "/commit.pkl"
        with open(commit_file, "wb") as f:
            pickle.dump(self.synapse_commit, f)

    def _load_active_commit(self) -> list:
        commit_file = "neurons/miner/active_commit.yaml"
        commit = yaml.load(open(commit_file), yaml.FullLoader)
        return commit


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info("Miner is running.")
            time.sleep(10)
