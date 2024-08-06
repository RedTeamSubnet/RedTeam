import torch
from generation_models.utils import (
    instantiate_from_config,
    pil_image_to_base64,
)
from typing import Dict, Any
import os
from PIL import Image


class ModelDeployment:
    def __init__(self, model_config):
        self.pipe = instantiate_from_config(model_config)

    async def generate(self, prompt_data: Dict[str, Any], image_format="PNG"):
        prompt_data = dict(prompt_data)
        generator = torch.manual_seed(prompt_data["seed"])
        output = self.pipe(
            generator=generator, **prompt_data, **prompt_data.get("pipeline_params", {})
        )
        if isinstance(output, Image.Image):
            base_64_image = pil_image_to_base64(output, image_format)
            return base_64_image
        elif isinstance(output, dict):
            return output
        else:
            raise ValueError("Unsupported output type")
