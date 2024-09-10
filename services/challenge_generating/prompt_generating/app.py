from fastapi import FastAPI
from pydantic import BaseModel, Extra
import argparse
from typing import Optional
import uvicorn
import random
import openai


class Prompt(BaseModel, extra=Extra.allow):
    prompt: str
    seed: Optional[int] = 0
    max_length: Optional[int] = 77
    model_name: Optional[str] = "OpenGeneral"


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


class ChallengePrompt:
    def __init__(self):
        self.app = FastAPI(title="Challenge Prompt")
        self.app.add_api_route("/", self.__call__, methods=["POST"])
        self.open_category_prefixes = {
            "OpenGeneral": [
                "an image of",
                "a landscape image of",
                "a painting of",
                "a drawing of",
                "a portrait photo of",
                "an illustration of",
                "a animated image of",
                "a sketch of",
            ],
            "OpenLandscape": [
                "an landscape image of",
                "a landscape photo of",
                "a landscape view of",
            ],
            "OpenDigitalArt": [
                "an digital art of",
                "a digital painting of",
                "a digital drawing of",
                "a digital illustration of",
                "a digital image of",
                "a digital sketch of",
            ],
        }

        self.vllm_client = openai.AsyncOpenAI(base_url="http://localhost:8000/v1")

    async def __call__(
        self,
        payload: Prompt,
    ):
        model_name = payload.model_name
        prompt = payload.prompt
        prompts = self.open_category_prefixes[model_name]
        prompt = random.choice(prompts)
        prompt = f"<|endoftext|> {prompt}"

        output = await self.vllm_client.completions.create(
            model="toilaluan/Image-Caption-Completion-Long",
            prompt=prompt,
            max_tokens=125,
            temperature=1.0,
            top_p=1,
            n=1,
            presence_penalty=0,
        )
        completed_prompt = output.choices[0].text.strip()
        completed_prompt = completed_prompt.replace("\n", " ")
        completed_prompt = completed_prompt.split(".")[:-1]
        completed_prompt = ".".join(completed_prompt) + "."

        return {"prompt": completed_prompt}


if __name__ == "__main__":
    args = get_args()
    print("Args: ", args)
    app = ChallengePrompt()
    uvicorn.run(app.app, host="0.0.0.0", port=args.port)
