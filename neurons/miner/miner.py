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
        self.active_challenges = self._get_active_challenges()
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
        commits = yaml.load(open(commit_file), yaml.FullLoader)
        if commits is None:
            return []
        valid_commits = self._check_format_commits(commits)
        return valid_commits

    def _check_format_commits(self, commits: list) -> list[str]:
        # Validate commit format
        valid_commits = []
        for commit in commits:
            if not isinstance(commit, str):
                bt.logging.warning(f"Invalid commit format (not a string): {commit}")
                continue

            # Check if commit follows the format: challenge_name---dockerhub_id@sha256:hash
            if not commit.count("---") == 1 or not commit.count("@sha256:") == 1:
                bt.logging.warning(f"Invalid commit format: {commit}")
                continue

            challenge_name, docker_info = commit.split("---")
            docker_id, sha = docker_info.split("@sha256:")

            if not challenge_name or not docker_id or not sha:
                bt.logging.warning(f"Invalid commit format (missing parts): {commit}")
                continue

            if challenge_name not in self.active_challenges:
                bt.logging.warning(
                    f"Invalid commit format (challenge not active): {commit}"
                )
                continue

            valid_commits.append(commit)
        return valid_commits


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info("Miner is running.")
            time.sleep(10)
