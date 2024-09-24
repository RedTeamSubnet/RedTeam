from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
import uvicorn
import argparse
import threading
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
import yaml
from functools import partial
import random
from services.owner_api_core import define_allowed_ips, filter_allowed_ips, limiter
from openai import OpenAI
import httpx
import traceback
import copy
import inspect

MODEL_CONFIG = yaml.load(
    open("generation_models/configs/model_config.yaml"), yaml.FullLoader
)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=10001)
    parser.add_argument("--netuid", type=str, default=23)
    parser.add_argument("--min_stake", type=int, default=100)
    parser.add_argument(
        "--chain_endpoint",
        type=str,
        default="finney",
    )
    parser.add_argument("--disable_secure", action="store_true")
    parser.add_argument(
        "--model_name",
        type=str,
        default="Pixtral_12b",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--vllm_url",
        type=str,
        default="http://localhost:8000",
    )
    parser.add_argument(
        "--vllm_api_key",
        type=str,
        default="apikey",
        help="api key of the VLLM service",
    )
    parser.add_argument(
        "--model_type",
        type=str,
        default="multimodal",
    )

    args = parser.parse_args()
    return args


class RewardRequest(BaseModel):
    miner_data: List[dict]
    base_data: dict


class VllmRewardApp:
    def __init__(self, args):
        self.args = args
        self.app = FastAPI()
        self.app.add_api_route("/", self.__call__, methods=["POST"])
        self.app.middleware("http")(partial(filter_allowed_ips, self))
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        self.allowed_ips = []

        if not self.args.disable_secure:
            self.allowed_ips_thread = threading.Thread(
                target=define_allowed_ips,
                args=(
                    self,
                    self.args.chain_endpoint,
                    self.args.netuid,
                    self.args.min_stake,
                ),
            )
            self.allowed_ips_thread.daemon = True
            self.allowed_ips_thread.start()

    def call_vllm(self, base_data):
        raise NotImplementedError("This method should be implemented by subclasses")
    
    def get_prompt_to_check(self, _base_data, base_prompt, miner_data, offset):
        raise NotImplementedError("This method should be implemented by subclasses")

    def prepare_testcase(self, base_data, miner_data):
        text_offset = miner_data["prompt_output"]["choices"][0]["logprobs"][
            "text_offset"
        ]
        n_tokens = len(text_offset)
        offset_idxs = [0] + [random.randint(1, n_tokens - 1) for _ in range(2)] + [-2]
        base_prompt = base_data["prompt"][0]
        same_keys = []
        n_logprobs = base_data["top_logprobs"] if "top_logprobs" in base_data else base_data["logprobs"]
        for offset_idx in offset_idxs:
            offset = text_offset[offset_idx]
            miner_top_logprobs = miner_data["prompt_output"]["choices"][0]["logprobs"][
                "top_logprobs"
            ][offset_idx]
            _base_data = base_data.copy()
            _base_data = self.get_prompt_to_check(_base_data, base_prompt, miner_data, offset)
            _base_data["max_tokens"] = 1
            valid_response = self.call_vllm(_base_data)
            valid_top_logprobs = valid_response["choices"][0]["logprobs"][
                "top_logprobs"
            ][0]
            same_keys.append(
                len(
                    set(miner_top_logprobs.keys()).intersection(
                        set(valid_top_logprobs.keys())
                    )
                )
            )
        print(same_keys, flush=True)
        average_same_keys: float = sum(same_keys) / len(same_keys) / n_logprobs
        print(average_same_keys, flush=True)
        return average_same_keys

    async def __call__(self, reward_request: RewardRequest):
        base_data = reward_request.base_data
        miner_data = reward_request.miner_data
        rewards = []
        for i, miner in enumerate(miner_data):
            try:
                average_same_keys: float = self.prepare_testcase(base_data, miner)
                reward = average_same_keys > self.args.threshold
                rewards.append(reward)
            except Exception as e:
                print(e)
                traceback.print_exc()
                rewards.append(False)
        return {"rewards": rewards}

class TextRewardApp(VllmRewardApp):
    def __init__(self, args):
        super().__init__(args)
        
    def call_vllm(self, base_data):
        with httpx.Client() as client:
            response = client.post(
                f"{self.args.vllm_url}/v1/completions",
                json=base_data,
                timeout=base_data.get("timeout", 32),
            )
            return response.json()

    def get_prompt_to_check(self, _base_data, base_prompt, miner_data, offset):
        prompt_to_check = (
            base_prompt + miner_data["prompt_output"]["choices"][0]["text"][:offset]
        )
        _base_data["prompt"] = [prompt_to_check]
        return _base_data

class MultiModalRewardApp(VllmRewardApp):
    def __init__(self, args):
        from services.utils import convert_chat_completion_response_to_completion_response
        self.convert_chat_completion_response_to_completion_response = convert_chat_completion_response_to_completion_response
        super().__init__(args)
        self.args.vllm_url += "/v1"
        self.client = OpenAI(
            base_url=self.args.vllm_url,
            api_key=self.args.vllm_api_key,
        )
        self.model_path = args.model_name

    def call_vllm(self, base_data):
        request = copy.deepcopy(base_data)
        if request["prompt_to_check"]:
            request["messages"].append({
                "role": "assistant",
                "content": request["prompt_to_check"],
                "prefix": True
            })
            request["extra_body"] = {
                "add_generation_prompt": False
            }
        valid_args = inspect.signature(self.client.chat.completions.create).parameters
        filtered_kwargs = {k: v for k, v in request.items() if k in valid_args}

        completion =self.client.chat.completions.create(**filtered_kwargs)
        return self.convert_chat_completion_response_to_completion_response(completion)

    def get_prompt_to_check(self, _base_data, base_prompt, miner_data, offset):
        prompt_to_check = miner_data["prompt_output"]["choices"][0]["text"][:offset]
        _base_data["prompt_to_check"] = prompt_to_check
        return _base_data




if __name__ == "__main__":
    args = get_args()
    if args.model_type == "multimodal":
        app = MultiModalRewardApp(args)
    else:
        app = TextRewardApp(args)
    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=args.port,
    )