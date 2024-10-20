import bittensor as bt
import json
import yaml
from .. import constants
from ..protocol import Commit
from typing import Tuple
from ..common import get_config
import os
import threading
import time
import traceback


class Miner:
    def __init__(self):
        self.config = get_config()
        self.setup_logging()
        self.setup_bittensor_objects()
        self.synapse_commit = self._load_synapse_commit()
        self.axon.attach(self.forward, self.blacklist)
        self.is_running = False

    def setup_logging(self):
        if self.config.logging.debug:
            bt.logging.enable_debug()
        if self.config.logging.trace:
            bt.logging.enable_trace()
        bt.logging(config=self.config, logging_dir=self.config.full_path)
        bt.logging.info(
            f"Running validator for subnet: {self.config.netuid} on network: {self.config.subtensor.network} with config:"
        )
        bt.logging.info(self.config)

    def setup_bittensor_objects(self):
        bt.logging.info("Setting up Bittensor objects.")
        self.wallet = bt.wallet(config=self.config)
        bt.logging.info(f"Wallet: {self.wallet}")
        self.subtensor = bt.subtensor(config=self.config)
        bt.logging.info(f"Subtensor: {self.subtensor}")
        self.dendrite = bt.dendrite(wallet=self.wallet)
        bt.logging.info(f"Dendrite: {self.dendrite}")
        self.metagraph = self.subtensor.metagraph(self.config.netuid)
        bt.logging.info(f"Metagraph: {self.metagraph}")
        self.axon = bt.axon(
            wallet=self.wallet, config=self.config, port=self.config.axon.port
        )
        bt.logging.info(f"Axon: {self.axon}")

        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(
                f"\nYour validator: {self.wallet} is not registered to chain connection: {self.subtensor} \nRun 'btcli register' and try again."
            )
            exit()
        else:
            self.my_subnet_uid = self.metagraph.hotkeys.index(
                self.wallet.hotkey.ss58_address
            )
            bt.logging.info(f"Running validator on uid: {self.my_subnet_uid}")

    def run(self):
        # Check that miner is registered on the network.
        self.metagraph.sync(subtensor=self.subtensor)

        # Serve passes the axon information to the network + netuid we are hosting on.
        # This will auto-update if the axon port of external ip have changed.
        bt.logging.info(
            f"Serving miner axon {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
        )
        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)

        # Start  starts the miner's axon, making it active on the network.
        self.axon.start()

    def run_in_background_thread(self):
        """
        Starts the miner's operations in a separate background thread.
        This is useful for non-blocking operations.
        """
        if not self.is_running:
            bt.logging.debug("Starting miner in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def stop_run_thread(self):
        """
        Stops the miner's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping miner in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        """
        Starts the miner's operations in a background thread upon entering the context.
        This method facilitates the use of the miner in a 'with' statement.
        """
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the miner's background operations upon exiting the context.
        This method facilitates the use of the miner in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        self.stop_run_thread()

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
