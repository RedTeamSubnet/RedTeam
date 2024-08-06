import numpy as np
import random
import torch
import time
import gc
import transformers
import diffusers
import os
from diffusers import KolorsPipeline
from controlnet_aux.processor import Processor
from .utils import resize_image, base64_to_pil_image
from .kolors import ControlNetModel, StableDiffusionXLControlNetImg2ImgPipeline
from optimum.quanto import freeze, qfloat8, quantize
from PIL import Image

MAX_SEED = np.iinfo(np.int32).max
MAX_IMAGE_SIZE = 2048
MAX_INFERENCE_STEPS = 50


class Kolors:
    class KolorsInput:
        def __init__(
            self,
            prompt="A board with the text 'It's NicheImage Time!'",
            generator=torch.Generator().manual_seed(random.randint(0, MAX_SEED)),
            width: int = 1024,
            height: int = 1024,
            guidance_scale: float = 5.0,
            num_inference_steps: int = 28,
            conditional_image: str = "",
            negative_prompt="",
            control_guidance_end=0.9,
            strength=1.0,
            controlnet_conditioning_scale: list = [0.8],
            ip_adapter_scale=0.0,
            pipeline_type="txt2img",
            **kwargs,
        ):
            self.prompt = prompt
            self.generator = generator
            self.width = width
            self.height = height
            self.guidance_scale = guidance_scale
            self.num_inference_steps = num_inference_steps
            self.conditional_image = self._process_conditional_image(conditional_image)
            self.negative_prompt = negative_prompt
            self.pipeline_type = pipeline_type
            self.controlnet_conditioning_scale = controlnet_conditioning_scale
            self.control_guidance_end = control_guidance_end
            self.strength = strength
            if pipeline_type == "ip_adapter":
                self.ip_adapter_scale = ip_adapter_scale
            else:
                self.ip_adapter_scale = 0.0
            self._check_inputs()

        def _process_conditional_image(self, conditional_image):
            if conditional_image:
                image = base64_to_pil_image(conditional_image)
                return resize_image(image, MAX_IMAGE_SIZE)
            return Image.new("RGB", (512, 512), "black")

        def _check_inputs(self):
            self.width = min(self.width, MAX_IMAGE_SIZE)
            self.height = min(self.height, MAX_IMAGE_SIZE)
            self.num_inference_steps = min(
                self.num_inference_steps, MAX_INFERENCE_STEPS
            )

    @torch.no_grad()
    def __init__(self, **kwargs):
        self.pipeline = self._load_pipeline()
        self.controlnet_pipeline, self.processors = self._load_controlnet_pipeline()

    def _load_pipeline(self):
        self.image_encoder = self._load_image_encoder()
        self.clip_image_processor = self._load_image_processor()
        pipeline = KolorsPipeline.from_pretrained(
            "Kwai-Kolors/Kolors-diffusers",
            torch_dtype=torch.float16,
            variant="fp16",
            image_encoder=self.image_encoder,
            feature_extractor=self.clip_image_processor,
        )
        start = time.time()
        quantize(pipeline.text_encoder, weights=qfloat8)
        freeze(pipeline.text_encoder)
        print(f"Quantizing text encoder took {time.time() - start:.2f} seconds")
        if hasattr(pipeline.unet, "encoder_hid_proj"):
            pipeline.unet.text_encoder_hid_proj = pipeline.unet.encoder_hid_proj
        self._load_ip_adapter(pipeline)
        start = time.time()
        quantize(pipeline.unet, weights=qfloat8)
        freeze(pipeline.unet)
        print(f"Quantizing UNet took {time.time() - start:.2f} seconds")
        pipeline.to("cuda")
        return pipeline

    def _load_image_encoder(self):
        return (
            transformers.CLIPVisionModelWithProjection.from_pretrained(
                "Kwai-Kolors/Kolors-IP-Adapter-Plus",
                subfolder="image_encoder",
                ignore_mismatched_sizes=True,
            )
            .to(dtype=torch.float16)
            .to("cuda")
        )

    def _load_image_processor(self):
        return transformers.CLIPImageProcessor(size=336, crop_size=336)

    def _load_controlnet_pipeline(self):
        canny_controlnet = ControlNetModel.from_pretrained(
            "Kwai-Kolors/Kolors-ControlNet-Canny", torch_dtype=torch.float16
        )
        depth_controlnet = ControlNetModel.from_pretrained(
            "Kwai-Kolors/Kolors-ControlNet-Depth", torch_dtype=torch.float16
        )
        start = time.time()
        quantize(canny_controlnet, weights=qfloat8)
        freeze(canny_controlnet)
        print(f"Quantizing Canny ControlNet took {time.time() - start:.2f} seconds")
        start = time.time()
        quantize(depth_controlnet, weights=qfloat8)
        freeze(depth_controlnet)
        print(f"Quantizing Depth ControlNet took {time.time() - start:.2f} seconds")
        controlnet_pipeline = StableDiffusionXLControlNetImg2ImgPipeline(
            vae=self.pipeline.vae,
            controlnet=[canny_controlnet, depth_controlnet],
            text_encoder=self.pipeline.text_encoder,
            tokenizer=self.pipeline.tokenizer,
            unet=self.pipeline.unet,
            scheduler=self.pipeline.scheduler,
            image_encoder=self.image_encoder,
            feature_extractor=self.clip_image_processor,
            force_zeros_for_empty_prompt=False,
        ).to("cuda")
        canny_processor = Processor("canny")
        depth_processor = Processor("depth_midas")
        depth_processor.processor.to("cuda")
        return controlnet_pipeline, [canny_processor, depth_processor]

    @torch.inference_mode()
    def __call__(self, *args, **kwargs):
        inputs = self.KolorsInput(**kwargs)
        self.pipeline.set_ip_adapter_scale(inputs.ip_adapter_scale)
        if inputs.pipeline_type == "controlnet":
            return self._run_controlnet_pipeline(inputs)
        else:
            return self._run_standard_pipeline(inputs)

    def _run_controlnet_pipeline(self, inputs):
        self.pipeline.set_ip_adapter_scale(inputs.ip_adapter_scale)
        processed_images = [
            processor(inputs.conditional_image) for processor in self.processors
        ]
        image = self.controlnet_pipeline(
            prompt=inputs.prompt,
            negative_prompt=inputs.negative_prompt,
            generator=inputs.generator,
            width=inputs.width,
            height=inputs.height,
            guidance_scale=inputs.guidance_scale,
            num_inference_steps=inputs.num_inference_steps,
            image=inputs.conditional_image,
            control_image=processed_images,
            controlnet_conditioning_scale=inputs.controlnet_conditioning_scale,
            control_guidance_end=inputs.control_guidance_end,
            strength=inputs.strength,
            ip_adapter_image=inputs.conditional_image,
        ).images[0]
        return image

    def _run_standard_pipeline(self, inputs):
        self.pipeline.set_ip_adapter_scale(inputs.ip_adapter_scale)
        image = self.pipeline(
            prompt=inputs.prompt,
            negative_prompt=inputs.negative_prompt,
            generator=inputs.generator,
            width=inputs.width,
            height=inputs.height,
            guidance_scale=inputs.guidance_scale,
            num_inference_steps=inputs.num_inference_steps,
            ip_adapter_image=inputs.conditional_image,
        ).images[0]
        return image

    def _load_ip_adapter(self, pipeline):
        pipeline.load_ip_adapter(
            "Kwai-Kolors/Kolors-IP-Adapter-Plus",
            subfolder="",
            weight_name=["ip_adapter_plus_general.bin"],
            low_cpu_mem_usage=True,
        )
