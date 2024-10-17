import bittensor as bt
from argparse import ArgumentParser
import json
import yaml
from .. import constants
from ..protocol import Commit
from ..common import get_config


class Miner:
    def __init__(self):
        self.config = get_config()
        self.subtensor = bt.subtensor(config=self.config)
        self.wallet = bt.wallet(config=self.config)
        self.metagraph = self.subtensor.metagraph(self.config.netuid)
        self.axon = bt.axon(config=self.config)
        self.synapse_commit = self._load_synapse_commit()
        self.axon.attach(self.forward, self.blacklist)
        self.axon.serve(self.config.netuid, self.subtensor)
        self.axon.start()

    def forward(self, synapse_commit: Commit) -> Commit:
        active_commits = self._load_active_commit()
        served_commits = list(self.synapse_commit.commit_dockers.keys())
        for commit in active_commits:
            if commit not in served_commits:
                self.synapse_commit.add_encrypted_commit(commit)
        return self.synapse_commit

    def blacklist(self, synapse_commit: Commit) -> bool:
        hotkey = synapse_commit.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        stake = self.metagraph.S[uid]
        if stake < constants.MIN_VALIDATOR_STAKE:
            return True, "Not enough stake"

        return False, "Passed"

    def _load_synapse_commit(self) -> Commit:
        commit_file = self.config.neuron.fullpath + "/commit.json"
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
