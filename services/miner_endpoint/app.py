from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel, Extra
import argparse
import uvicorn
from ray.serve.handle import DeploymentHandle
from ray import serve
import yaml
from services.rays.image_generating import ModelDeployment
import asyncio

MODEL_CONFIG = yaml.load(
    open("generation_models/configs/model_config.yaml"), yaml.FullLoader
)


class RequestCancelledMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Let's make a shared queue for the request messages
        queue = asyncio.Queue()

        async def message_poller(sentinel, handler_task):
            nonlocal queue
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    handler_task.cancel()
                    return sentinel  # Break the loop

                # Puts the message in the queue
                await queue.put(message)

        sentinel = object()
        handler_task = asyncio.create_task(self.app(scope, queue.get, send))
        asyncio.create_task(message_poller(sentinel, handler_task))

        try:
            return await handler_task
        except asyncio.CancelledError:
            print("Cancelling request due to disconnect")


class Prompt(BaseModel, extra=Extra.allow):
    prompt: str
    seed: int
    pipeline_type: str
    pipeline_params: Optional[dict] = {}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=10006)
    parser.add_argument(
        "--bind_ip",
        type=str,
        default="0.0.0.0",
        help="IP address to run the service on",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="RealisticVision",
    )
    parser.add_argument("--num_gpus", type=float, default=1.0)
    parser.add_argument("--num_cpus", type=float, default=1.0)
    parser.add_argument("--num_replicas", type=int, default=1)
    args = parser.parse_args()
    return args


args = get_args()


class MinerEndpoint:
    def __init__(self, model_handle: DeploymentHandle):
        self.model_handle = model_handle
        self.app = FastAPI()
        self.app.add_api_route("/generate", self.generate, methods=["POST"])
        self.app.add_api_route("/info", self.info, methods=["GET"])
        self.app.add_middleware(RequestCancelledMiddleware)

    async def generate(self, prompt: Prompt):
        prompt_data = prompt.dict()
        image_format = prompt_data["pipeline_params"].pop("image_format", "JPG")
        output = await self.model_handle.generate.remote(
            prompt_data=prompt_data, image_format=image_format
        )
        if isinstance(output, dict):
            return {"response_dict": output}
        if isinstance(output, str):
            return {"image": output}
        raise ValueError("Unsupported output type")

    async def info(self):
        return {
            "model_name": args.model_name,
        }


if __name__ == "__main__":
    model_deployment = serve.deployment(
        ModelDeployment,
        name="deployment",
        num_replicas=args.num_replicas,
        ray_actor_options={"num_gpus": args.num_gpus, "num_cpus": args.num_cpus},
        max_ongoing_requests=1,
    )
    serve.run(
        model_deployment.bind(
            MODEL_CONFIG[args.model_name],
        ),
        name=f"deployment-{args.model_name}",
    )
    model_handle = serve.get_deployment_handle(
        "deployment", f"deployment-{args.model_name}"
    )
    app = MinerEndpoint(model_handle)
    uvicorn.run(
        app.app,
        host=args.bind_ip,
        port=args.port,
    )
