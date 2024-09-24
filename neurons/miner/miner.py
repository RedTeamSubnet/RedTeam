import time
from typing import Tuple, TypeVar
import bittensor as bt
from image_generation_subnet.base.miner import BaseMinerNeuron
import image_generation_subnet
from image_generation_subnet.protocol import (
    ImageGenerating,
    TextGenerating,
    MultiModalGenerating,
    Information,
)
import traceback

T = TypeVar("T", bound=bt.Synapse)


class Miner(BaseMinerNeuron):
    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        self.validator_logs = {}
        self.volume_per_validator = (
            image_generation_subnet.utils.volume_setting.get_volume_per_validator(
                self.metagraph,
                self.config.miner.total_volume,
                self.config.miner.size_preference_factor,
                self.config.miner.min_stake,
            )
        )
        self.miner_info = image_generation_subnet.miner.set_info(self)
        self.num_processing_requests = 0
        self.total_request_in_interval = 0
        bt.logging.info(f"Miner info: {self.miner_info}")

    async def forward_image(self, synapse: ImageGenerating) -> ImageGenerating:
        if "get_miner_info" in synapse.request_dict:
            return await self.forward_info_legacy(synapse)
        self.num_processing_requests += 1
        self.total_request_in_interval += 1
        try:
            bt.logging.info(
                f"Processing {self.num_processing_requests} requests, synapse prompt: {synapse.prompt}"
            )
            synapse.limit_params()
            synapse = await image_generation_subnet.miner.generate(self, synapse)
            self.num_processing_requests -= 1
        except Exception as e:
            bt.logging.warning(f"Error in forward_image: {e}")
            self.num_processing_requests -= 1
        return synapse

    async def forward_info_legacy(self, synapse: ImageGenerating) -> ImageGenerating:
        synapse.response_dict = self.miner_info
        bt.logging.info(f"Response dict: {self.miner_info}")
        validator_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        bt.logging.info(
            f"Request counter for {validator_uid}: {self.validator_logs[validator_uid]['request_counter']}/{self.validator_logs[validator_uid]['max_request']}"
        )
        self.validator_logs[validator_uid]["request_counter"] = (
            self.validator_logs[validator_uid].get("request_counter", 0) - 1
        )
        bt.logging.info(
            f"Request counter for {validator_uid}: {self.validator_logs[validator_uid]['request_counter']}/{self.validator_logs[validator_uid]['max_request']}"
        )
        return synapse

    async def forward_text(self, synapse: TextGenerating) -> TextGenerating:
        if synapse.request_dict:
            return await self.forward_info_legacy(synapse)
        self.num_processing_requests += 1
        self.total_request_in_interval += 1
        try:
            bt.logging.info(
                f"Processing {self.num_processing_requests} requests, synapse input: {synapse.prompt_input}"
            )
            synapse.limit_params()
            synapse = await image_generation_subnet.miner.generate(self, synapse)
            self.num_processing_requests -= 1
        except Exception as e:
            bt.logging.warning(f"Error in forward_text: {e}")
            self.num_processing_requests -= 1
        return synapse

    async def forward_multimodal(self, synapse: MultiModalGenerating) -> MultiModalGenerating:
        if synapse.request_dict:
            return await self.forward_info_legacy(synapse)
        self.num_processing_requests += 1
        self.total_request_in_interval += 1
        try:
            bt.logging.info(
                f"Processing {self.num_processing_requests} requests, synapse input: {synapse.prompt}"
            )
            synapse.limit_params()
            synapse = await image_generation_subnet.miner.generate(self, synapse)
            self.num_processing_requests -= 1
        except Exception as e:
            bt.logging.warning(f"Error in forward_multimodal: {e}")
            self.num_processing_requests -= 1
        return synapse

    async def forward_info(self, synapse: Information) -> Information:
        synapse.response_dict = self.miner_info
        return synapse

    async def blacklist_info(self, synapse: Information) -> Tuple[bool, str]:
        return False, "All passed!"

    async def blacklist(self, synapse: ImageGenerating) -> Tuple[bool, str]:
        bt.logging.info(f"synapse in blacklist {synapse}")
        try:
            if synapse.dendrite.hotkey not in self.metagraph.hotkeys:
                # Ignore requests from unrecognized entities.
                bt.logging.trace(
                    f"Blacklisting unrecognized hotkey {synapse.dendrite.hotkey}"
                )
                return True, "Unrecognized hotkey"
            if (
                self.num_processing_requests
                >= self.config.miner.max_concurrent_requests
            ):
                bt.logging.info(
                    f"Serving {self.num_processing_requests} requests, max concurrent requests: {self.config.miner.max_concurrent_requests}"
                )
                bt.logging.trace(
                    f"Blacklisting {synapse.dendrite.hotkey} for exceeding the limit of concurrent requests"
                )
                return True, "Max concurrent requests exceeded"

            validator_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
            stake = self.metagraph.stake[validator_uid].item()

            if validator_uid not in self.volume_per_validator:
                bt.logging.trace(
                    f"Blacklisting {validator_uid}-validator has {stake} stake"
                )
                return True, "Not enough stake"
            if image_generation_subnet.miner.check_limit(
                self,
                uid=validator_uid,
                stake=stake,
                volume_per_validator=self.volume_per_validator,
                interval=self.config.miner.limit_interval,
            ):
                bt.logging.trace(
                    f"Blacklisting {validator_uid}-validator for exceeding the limit"
                )
                return True, "Limit exceeded"

            return False, "All passed!"
        except Exception as e:
            bt.logging.error(f"Error in blacklist: {e}")
            traceback.print_exc()
            return False, "All passed!"

    async def blacklist_image(self, synapse: ImageGenerating) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_text(self, synapse: TextGenerating) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_multimodal(self, synapse: MultiModalGenerating) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def priority(self, synapse: ImageGenerating) -> float:
        caller_uid = self.metagraph.hotkeys.index(
            synapse.dendrite.hotkey
        )  # Get the caller index.
        prirority = float(
            self.metagraph.S[caller_uid]
        )  # Return the stake as the priority.
        bt.logging.trace(
            f"Prioritizing {synapse.dendrite.hotkey} with value: ", prirority
        )
        return prirority


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        start_time = time.time()
        while True:
            bt.logging.info("Miner running...", time.time())
            if time.time() - start_time > 300:
                bt.logging.info(
                    f"---Total request in last 5 minutes: {miner.total_request_in_interval}"
                )
                start_time = time.time()
                miner.total_request_in_interval = 0
            try:
                bt.logging.debug("Syncing metagraph")
                miner.resync_metagraph()
                bt.logging.debug("Synced metagraph")
                miner.volume_per_validator = image_generation_subnet.utils.volume_setting.get_volume_per_validator(
                    miner.metagraph,
                    miner.config.miner.total_volume,
                    miner.config.miner.size_preference_factor,
                    miner.config.miner.min_stake,
                    log=False,
                )
            except Exception as e:
                print(e)
            time.sleep(60)
