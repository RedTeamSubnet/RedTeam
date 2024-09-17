import bittensor as bt
from image_generation_subnet.protocol import ImageGenerating, Information
import torch
from image_generation_subnet.utils.volume_setting import get_volume_per_validator
import requests
from threading import Thread
import image_generation_subnet as ig_subnet

class MinerManager:
    def __init__(self, validator):
        self.validator = validator
        self.all_uids = [int(uid.item()) for uid in self.validator.metagraph.uids]
        self.all_uids_info = {
            uid: {"scores": [], "model_name": "", "process_time": []} for uid in self.all_uids
        }
    
    def get_miner_info(self):
        """
        1. Query model_name of available uids
        """
        self.all_uids = [int(uid) for uid in self.validator.metagraph.uids]
        uid_to_axon = dict(zip(self.all_uids, self.validator.metagraph.axons))
        query_axons = [uid_to_axon[int(uid)] for uid in self.all_uids]
        synapse = Information()
        bt.logging.info("Requesting miner info using synapse Information")
        responses = self.validator.dendrite.query(
            query_axons,
            synapse,
            deserialize=False,
            timeout=10,
        )
        responses = {
            uid: response.response_dict
            for uid, response in zip(self.all_uids, responses)
        }
        remaining_uids = [uid for uid, info in responses.items() if not info]

        if remaining_uids:
            bt.logging.warning(f"Querying legacy for {len(remaining_uids)} remaining uids.")
            remaining_axons = [uid_to_axon[uid] for uid in remaining_uids]
            synapse = ImageGenerating()
            synapse.request_dict = {"get_miner_info": True}
            responses_legacy = self.validator.dendrite.query(
                remaining_axons,
                synapse,
                deserialize=False,
                timeout=10,
            )
            responses_legacy = {
                uid: response.response_dict
                for uid, response in zip(remaining_uids, responses_legacy)
            }
            responses.update(responses_legacy)
        responses = {k: v for k, v in responses.items() if v}
        return responses

    def update_miners_identity(self):
        """
        1. Query model_name of available uids
        2. Update the available list
        """
        valid_miners_info = self.get_miner_info()
        if not valid_miners_info:
            bt.logging.warning("No active miner available. Skipping setting weights.")
        for uid, info in valid_miners_info.items():
            miner_state = self.all_uids_info.setdefault(
                uid,
                {
                    "scores": [],
                    "model_name": "",
                    "process_time": []
                },
            )
            model_name = info.get("model_name", "")
            miner_state["total_volume"] = info.get("total_volume", 40)
            miner_state["min_stake"] = info.get("min_stake", 10000)
            miner_state["reward_scale"] = max(
                min(miner_state["total_volume"] ** 0.5 / 1000**0.5, 1), 0
            )
            miner_state["device_info"] = info.get("device_info", {})

            volume_per_validator = get_volume_per_validator(
                self.validator.metagraph,
                miner_state["total_volume"],
                1.03,
                10000,
                False,
            )
            miner_state["rate_limit"] = volume_per_validator.get(self.validator.uid, 2)
            bt.logging.info(f"Rate limit for {uid}: {miner_state['rate_limit']}")
            if miner_state["model_name"] == model_name:
                continue
            miner_state["model_name"] = model_name
            miner_state["scores"] = []
            miner_state["process_time"] = []

        bt.logging.success("Updated miner identity")
        model_distribution = {}
        for uid, info in self.all_uids_info.items():
            model_distribution[info["model_name"]] = (
                model_distribution.get(info["model_name"], 0) + 1
            )
        # Remove all key type is str, keep only int from all_uids_info
        self.all_uids_info = {
            int(k): v for k, v in self.all_uids_info.items() if isinstance(k, int)
        }
        bt.logging.info(f"Model distribution: {model_distribution}")
        thread = Thread(target=self.store_miner_info, daemon=True)
        thread.start()

    def get_miner_uids(self, model_name: str):
        available_uids = [
            int(uid)
            for uid in self.all_uids_info.keys()
            if self.all_uids_info[uid]["model_name"] == model_name
        ]
        return available_uids

    def update_scores(self, uids, rewards):
        for uid, reward in zip(uids, rewards):
            self.all_uids_info[uid]["scores"].append(reward)
            self.all_uids_info[uid]["scores"] = self.all_uids_info[uid]["scores"][-10:]

    def update_metadata(self, uids, process_times):
        for uid, ptime in zip(uids, process_times):
            if "process_time" not in self.all_uids_info[uid]:
                self.all_uids_info[uid]["process_time"] = []
            self.all_uids_info[uid]["process_time"].append(ptime)
            self.all_uids_info[uid]["process_time"] = self.all_uids_info[uid]["process_time"][-500:]

    def get_model_specific_weights(self, model_name, normalize=True):
        model_specific_weights = torch.zeros(len(self.all_uids))
        for uid in self.get_miner_uids(model_name):
            num_past_to_check = 10
            model_specific_weights[int(uid)] = (
                sum(self.all_uids_info[uid]["scores"][-num_past_to_check:])
                / num_past_to_check
            )
        model_specific_weights = torch.clamp(model_specific_weights, 0, 1)
        if normalize:
            tensor_sum = torch.sum(model_specific_weights)
            # Normalizing the tensor
            if tensor_sum > 0:
                model_specific_weights = model_specific_weights / tensor_sum
        return model_specific_weights

    def store_miner_info(self):
        try:
            catalogue = {}
            for k, v in self.validator.nicheimage_catalogue.items():
                catalogue[k] = {
                    "model_incentive_weight": v.get("model_incentive_weight", 0),
                    "supporting_pipelines": v.get("supporting_pipelines", []),
                }
            requests.post(
                self.validator.config.storage_url + "/store_miner_info",
                json={
                    "uid": self.validator.uid,
                    "info": self.all_uids_info,
                    "version": ig_subnet.__version__,
                    "catalogue": catalogue,
                },
            )
            self.reset_metadata()
        except Exception as e:
            bt.logging.error(f"Failed to store miner info: {e}")

    def reset_metadata(self):
        for uid in self.all_uids_info:
            self.all_uids_info[uid]["process_time"] = []
 
