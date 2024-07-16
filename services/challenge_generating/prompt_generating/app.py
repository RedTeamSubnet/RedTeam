from fastapi import FastAPI
from pydantic import BaseModel, Extra
import argparse
from typing import Optional
import uvicorn
from services.challenge_generating.prompt_generating.model import ChallengePromptGenerator

class Prompt(BaseModel, extra=Extra.allow):
    prompt: str
    seed: Optional[int] = 0
    max_length: Optional[int] = 77


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11277)
    parser.add_argument("--netuid", type=str, default=23)
    parser.add_argument("--min_stake", type=int, default=100)
    parser.add_argument(
        "--chain_endpoint",
        type=str,
        default="finney",
    )
    parser.add_argument("--disable_secure", action="store_true", default=False)
    args = parser.parse_args()
    return args


class ChallengeImage:
    def __init__(self):
        self.challenge_prompt = ChallengePromptGenerator()
        self.app = FastAPI(title="Challenge Prompt")
        self.app.add_api_route("/", self.__call__, methods=["POST"])

    async def __call__(
        self,
        data: Prompt,
    ):
        data = dict(data)
        prompt = data["prompt"]
        if not prompt:
            prompt = "an image of "
        complete_prompt = self.challenge_prompt.infer_prompt([prompt], max_generation_length=77, sampling_topk=100)[0].strip()
        return {"prompt": complete_prompt}

if __name__ == '__main__':
    args = get_args()
    print("Args: ",args)
    app = ChallengeImage()
    uvicorn.run(app.app, host="0.0.0.0", port=args.port)