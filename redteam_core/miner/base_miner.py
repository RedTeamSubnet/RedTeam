import pathlib
import time
import threading
from abc import ABC, abstractmethod
from typing import Tuple

import yaml
import bittensor as bt

from ..protocol import Commit
from ..common import get_config


class BaseMiner(ABC):
    def __init__(self):
        self.config = get_config()
        self.setup_logging()
        self.setup_bittensor_objects()
        self.axon.attach(self.forward, self.blacklist)
        self.is_running = False

    def setup_logging(self):
        bt.logging.enable_default()
        bt.logging.enable_info()
        if self.config.logging.debug:
            bt.logging.enable_debug()
        if self.config.logging.trace:
            bt.logging.enable_trace()
        bt.logging(config=self.config, logging_dir=self.config.full_path)
        bt.logging.info(
            f"Running miner for subnet: {self.config.netuid} on network: {self.config.subtensor.network} with config:"
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
                f"\nYour miner: {self.wallet} is not registered to chain connection: {self.subtensor} \nRun 'btcli register' and try again."
            )
            exit()
        else:
            self.my_subnet_uid = self.metagraph.hotkeys.index(
                self.wallet.hotkey.ss58_address
            )
            bt.logging.info(f"Running miner on uid: {self.my_subnet_uid}")

    def run(self):
        # Check that miner is registered on the network.
        self.metagraph.sync(subtensor=self.subtensor)
        last_sync = time.time()

        # Serve passes the axon information to the network + netuid we are hosting on.
        # This will auto-update if the axon port of external ip have changed.
        bt.logging.info(
            f"Serving miner axon {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
        )
        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)

        # Start  starts the miner's axon, making it active on the network.
        self.axon.start()

        while True:
            RESYNC_INTERVAL = 600  # resync every 10 minutes
            SLEEP_TIME = 30

            try:
                if time.time() - last_sync > RESYNC_INTERVAL:
                    bt.logging.info("Resyncing metagraph...")
                    self.metagraph.sync(subtensor=self.subtensor)
                    bt.logging.info(
                        f"Resynced metagraph Block: {self.metagraph.block.item()}"
                    )
                    last_sync = time.time()
                time.sleep(SLEEP_TIME)

            except KeyboardInterrupt:
                self.axon.stop()
                bt.logging.success("Miner killed by keyboard interrupt.")
                break
            except Exception as e:
                bt.logging.error(f"Miner exception: {e}")

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

    def _get_active_challenges(self):
        active_challenges_path = (
            pathlib.Path(__file__).parent.parent
            / "challenge_pool"
            / "active_challenges.yaml"
        )
        with open(active_challenges_path, "r") as f:
            active_challenges = yaml.load(f, yaml.FullLoader)
        active_challenges = list(active_challenges.keys())
        bt.logging.info(f"Active challenges: {active_challenges}")
        return active_challenges

    @abstractmethod
    def forward(self, synapse: Commit) -> Commit: ...

    @abstractmethod
    def blacklist(self, synapse: Commit) -> Tuple[bool, str]: ...
