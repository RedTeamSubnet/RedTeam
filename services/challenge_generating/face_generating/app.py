import torch
from fastapi import FastAPI
from pydantic import BaseModel, Extra
import uvicorn
import argparse
import threading
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from generation_models.utils import pil_image_to_base64
from typing import Optional
from ray import serve
from ray.serve.handle import DeploymentHandle
from functools import partial
from services.owner_api_core import define_allowed_ips, filter_allowed_ips, limiter
from services.challenge_generating.face_generating.generate_face import FaceGenerator

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11278)
    parser.add_argument("--netuid", type=str, default=23)
    parser.add_argument("--min_stake", type=int, default=100)
    parser.add_argument(
        "--chain_endpoint",
        type=str,
        default="finney",
    )
    parser.add_argument("--disable_secure", action="store_true", default=False)
    parser.add_argument(
        "--num_gpus",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--num_replicas",
        type=int,
        default=1,
    )
    args = parser.parse_args()
    return args


class ImageGenerator:
    def __init__(self):
        self.pipe = FaceGenerator()

    async def __call__(self, data: dict):
        image = self.pipe()
        image = pil_image_to_base64(image)
        return image


class ChallengeImage:
    def __init__(self, model_handle: DeploymentHandle, args):
        self.args = args
        self.model_handle = model_handle
        self.app = FastAPI(title="Challenge Image")
        self.app.add_api_route("/", self.__call__, methods=["POST"])
        self.app.middleware("http")(partial(filter_allowed_ips, self))
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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

    async def __call__(
        self,
        data: dict,
    ):
        data = dict(data)
        image = await self.model_handle.remote(data)
        return {"conditional_image": image}


if __name__ == "__main__":
    args = get_args()
    print(args)
    model_deployment = serve.deployment(
        ImageGenerator,
        name="deployment",
        num_replicas=args.num_replicas,
        ray_actor_options={"num_gpus": args.num_gpus},
    )
    serve.run(
        model_deployment.bind(),
        name="deployment-image-challenge",
    )
    model_handle = serve.get_deployment_handle(
        "deployment", "deployment-image-challenge"
    )
    app = ChallengeImage(model_handle, args)
    uvicorn.run(app.app, host="0.0.0.0", port=args.port)
