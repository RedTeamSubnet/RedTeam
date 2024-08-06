import requests
import bittensor as bt
from image_generation_subnet.protocol import ImageGenerating
from typing import List
from math import pow
from functools import wraps
from tqdm import tqdm
import httpx
import json

def retry(**kwargs):
    module = kwargs.get("module", "unknown")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # retry forever
            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    bt.logging.error(f"Error in {module}: {e}, retrying...")

        return wrapper

    return decorator


def skip(**kwargs):
    module = kwargs.get("module", "unknown")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # return None if error
            try:
                return f(*args, **kwargs)
            except Exception as e:
                bt.logging.error(f"Error in {module}: {e}, skipping...")
                return None

        return wrapper

    return decorator


def get_challenge(
    url: str, synapses: List[ImageGenerating], backup_func: callable
) -> List[ImageGenerating]:
    for i, synapse in tqdm(enumerate(synapses), total=len(synapses)):
        if not synapse:
            continue
        try:
            data = synapse.deserialize()
            with httpx.Client(timeout=httpx.Timeout(60)) as client:
                response = client.post(url, json=data)
            if response.status_code != 200:
                challenge = backup_func()
            else:
                challenge = response.json()
        except Exception as e:
            bt.logging.warning(f"Error in get_challenge: {e}")
            challenge = backup_func()
        if challenge:
            synapses[i] = synapse.copy(update=challenge)
        else:
            synapses[i] = None
    return synapses

def get_reward_offline(
    base_synapse: ImageGenerating,
    synapses: List[ImageGenerating],
    uids: List[int],
    timeout: float,
    message_broker
):
    """Push synapse responses into a Redis stream to calculate rewards offline for miners ."""
    valid_uids = [uid for uid, response in zip(uids, synapses) if response.is_success]
    invalid_uids = [
        uid for uid, synapse in zip(uids, synapses) if not synapse.is_success
    ]
    valid_synapses = [synapse for synapse in synapses if synapse.is_success]
   
    miner_data = []
    for synapse in valid_synapses:
        dt = synapse.deserialize()
        dt["process_time"] = synapse.dendrite.process_time
        miner_data.append(dt)
    
    all_miner_data = [synapse.deserialize() for synapse in synapses]
    data = {
        "timeout": timeout,
        "valid_uids": valid_uids,
        "invalid_uids": invalid_uids,
        "miner_data": miner_data,
        "base_data": base_synapse.deserialize_input(),
        "uids": uids,
        "all_miner_data": all_miner_data
    }
    try:
        message_broker.publish_to_stream(stream_name = "synapse_data", message = {"data": json.dumps(data)})
    except Exception as ex:
        bt.logging.error(f"Push synapse result to message broker fail: {str(ex)} ")


def get_reward(
    url: str,
    base_synapse: ImageGenerating,
    synapses: List[ImageGenerating],
    uids: List[int],
    timeout: float,
    miner_manager,
) -> List[float]:
    valid_uids = [uid for uid, response in zip(uids, synapses) if response.is_success]
    invalid_uids = [
        uid for uid, synapse in zip(uids, synapses) if not synapse.is_success
    ]
    total_uids = valid_uids + invalid_uids
    valid_synapses = [synapse for synapse in synapses if synapse.is_success]
    if valid_uids:
        data = {
            "miner_data": [synapse.deserialize() for synapse in valid_synapses],
            "base_data": base_synapse.deserialize_input(),
        }
        with httpx.Client(timeout=httpx.Timeout(120, connect=8)) as client:
            response = client.post(url, json=data)
        if response.status_code != 200:
            raise Exception(f"Error in get_reward: {response.json()}")
        valid_rewards = response.json()["rewards"]
        valid_rewards = [float(reward) for reward in valid_rewards]
        process_times = [synapse.dendrite.process_time for synapse in valid_synapses]
        if timeout > 12:
            valid_rewards = add_time_penalty(valid_rewards, process_times, 0.4, timeout)
        else:
            valid_rewards = add_time_penalty(valid_rewards, process_times, 0.4, timeout)
        valid_rewards = [round(num, 3) for num in valid_rewards]
    else:
        bt.logging.info("0 valid responses in a batch")
        valid_rewards = []

    total_rewards = valid_rewards + [0] * len(invalid_uids)

    return total_uids, total_rewards


def add_time_penalty(rewards, process_times, max_penalty=0.4, factor: float = 12):
    """
    Add time penalty to rewards, based on process time
    """
    penalties = [
        max_penalty * pow(process_time, 1.5) / pow(factor, 1.5)
        for process_time in process_times
    ]
    penalties = [min(penalty, max_penalty) for penalty in penalties]
    for i in range(len(rewards)):
        if rewards[i] > 0:
            rewards[i] = rewards[i] - penalties[i]
    return rewards
