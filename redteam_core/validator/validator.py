import threading
import time
import traceback
from abc import ABC, abstractmethod

import bittensor as bt
from substrateinterface import SubstrateInterface

from ..constants import constants


class BaseValidator(ABC):
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        self.setup_bittensor_objects()
        self.last_update = 0
        self.current_block = 0
        self.node = SubstrateInterface(url=self.config.subtensor.chain_endpoint)
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

        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(
                f"\nYour validator: {self.wallet} is not registered to chain connection: {self.subtensor} \nRun 'btcli register' and try again."
            )
            exit()
        else:
            self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
            bt.logging.info(f"Running validator on uid: {self.uid}")

    def node_query(self, module, method, params):
        try:
            result = self.node.query(module, method, params).value

        except Exception:
            # reinitilize node
            self.node = SubstrateInterface(url=self.config.subtensor.chain_endpoint)
            result = self.node.query(module, method, params).value

        return result

    def synthetic_loop_in_background_thread(self):
        """
        Starts the validator's operations in a background thread upon entering the context.
        This method facilitates the use of the validator in a 'with' statement.
        """
        if not self.is_running:
            bt.logging.debug("Starting validator in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def __enter__(self):
        self.synthetic_loop_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the validator's background operations upon exiting the context.
        This method facilitates the use of the validator in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    @abstractmethod
    def forward(self):
        pass

    def run(self):
        bt.logging.info("Starting validator loop.")
        # Try set weights after initial sync
        try:
            bt.logging.info("Initializing weights")
            self.set_weights()
        except Exception:
            bt.logging.error(f"Initial set weights error: {traceback.format_exc()}")

        while True:
            start_epoch = time.time()

            try:
                self.forward()
                bt.logging.success("Forward completed")
            except Exception:
                bt.logging.error(f"Forward error: {traceback.format_exc()}")

            end_epoch = time.time()
            elapsed = end_epoch - start_epoch
            time_to_sleep = max(0, constants.EPOCH_LENGTH - elapsed)
            bt.logging.info(f"Epoch finished. Sleeping for {time_to_sleep} seconds.")
            time.sleep(time_to_sleep)

            try:
                self.set_weights()
                bt.logging.success("Set weights completed")
            except Exception:
                bt.logging.error(f"Set weights error: {traceback.format_exc()}")

            try:
                self.resync_metagraph()
                bt.logging.success("Resync metagraph completed")
            except Exception:
                bt.logging.error(f"Resync metagraph error: {traceback.format_exc()}")

            except KeyboardInterrupt:
                bt.logging.success("Keyboard interrupt detected. Exiting validator.")
                exit()

    @abstractmethod
    def set_weights(self):
        pass

    def resync_metagraph(self):
        self.metagraph.sync()
