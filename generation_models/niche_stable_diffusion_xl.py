import diffusers
from PIL import Image
from .base_model import BaseModel
from .utils import (
    download_checkpoint,
    base64_to_pil_image,
    resize_for_condition_image,
    set_scheduler,
)
import os
import torch
import sys
import bittensor as bt

class NicheStableDiffusionXL(BaseModel):
    def load_model(self, checkpoint_file, download_url, supporting_pipelines, **kwargs):
        if not os.path.exists(checkpoint_file):
            download_checkpoint(download_url, checkpoint_file)

        txt2img_pipe = diffusers.StableDiffusionXLPipeline.from_single_file(
            checkpoint_file,
            use_safetensors=True,
            torch_dtype=torch.float16,
        )
        scheduler_name = kwargs.get("scheduler", "euler_a")
        txt2img_pipe.scheduler = set_scheduler(
            scheduler_name, txt2img_pipe.scheduler.config
        )
        txt2img_pipe.to("cuda")


        img2img_pipe = self.load_img2img(txt2img_pipe.components, supporting_pipelines)
        instant_id_pipe = self.load_instantid_pipeline(txt2img_pipe.components, supporting_pipelines)
        controlnet_pipe = self.load_controlnet_pipeline(txt2img_pipe.components, supporting_pipelines)

        pipelines = {
            "txt2img": txt2img_pipe,
            "img2img": img2img_pipe,
            "instantid": instant_id_pipe,
            "controlnet": controlnet_pipe,
        }

        def inference_function(*args, **kwargs) -> Image.Image:
            pipeline_type = kwargs["pipeline_type"]
            pipeline = pipelines[pipeline_type]
            if not pipeline:
                raise ValueError(f"Pipeline type {pipeline_type} is not supported")
            
            output = pipeline(*args, **kwargs)
            if output is None:
                return Image.new("RGB", (512, 512), (255, 255, 255))
            return output.images[0]

        return inference_function

    def load_img2img(self, components, supporting_pipelines) -> callable:
        if "img2img" not in supporting_pipelines:
            return None
        img2img_pipe = diffusers.StableDiffusionXLImg2ImgPipeline(**components)
        img2img_pipe.to("cuda")

        def inference_function(*args, **kwargs):
            conditional_image = self.process_conditional_image(**kwargs)
            width, height = conditional_image.size
            kwargs.update(
                {
                    "image": conditional_image,
                    "width": width,
                    "height": height,
                }
            )
            return img2img_pipe(*args, **kwargs)

        return inference_function

    def load_instantid_pipeline(self, components, supporting_pipelines) -> callable:
        if "instantid" not in supporting_pipelines:
            return None

        from huggingface_hub import hf_hub_download
        hf_hub_download(repo_id="InstantX/InstantID", filename="ControlNetModel/config.json", local_dir="checkpoints/InstantID")
        hf_hub_download(repo_id="InstantX/InstantID", filename="ControlNetModel/diffusion_pytorch_model.safetensors", local_dir="checkpoints/InstantID")
        hf_hub_download(repo_id="InstantX/InstantID", filename="ip-adapter.bin", local_dir="checkpoints/InstantID")

        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name='antelopev2', root='checkpoints/insightface', providers=['CUDAExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))

        sys.path.append("generation_models/custom_pipelines/InstantID")
        import cv2
        import numpy as np
        from pipeline_stable_diffusion_xl_instantid import StableDiffusionXLInstantIDPipeline, draw_kps

        controlnet_path = "checkpoints/InstantID/ControlNetModel"
        face_adapter = "checkpoints/InstantID/ip-adapter.bin"
        controlnet = diffusers.ControlNetModel.from_pretrained(controlnet_path, torch_dtype=torch.float16, local_files_only=True)
        pipe = StableDiffusionXLInstantIDPipeline(**components, controlnet=controlnet)
        pipe.to("cuda")
        pipe.load_ip_adapter_instantid(face_adapter)
        pipe.set_ip_adapter_scale(0)

        def inference_function(*args, **kwargs):
            conditional_image: Image.Image = self.process_conditional_image(resolution=512, **kwargs)
            face_info = app.get(cv2.cvtColor(np.array(conditional_image), cv2.COLOR_RGB2BGR))
            controlnet_conditioning_scale = kwargs.get("controlnet_conditioning_scale", 0.8)
            ip_adapter_scale = kwargs.get("ip_adapter_scale", 0.8)
            if len(face_info) == 0:
                bt.logging.info("No face detected in the image")
                conditional_image = Image.open("assets/images/image.png")
                face_info = app.get(cv2.cvtColor(np.array(conditional_image), cv2.COLOR_RGB2BGR))
                ip_adapter_scale = 0.0
                controlnet_conditioning_scale = 0.0
            pipe.set_ip_adapter_scale(ip_adapter_scale)
            face_info = sorted(face_info, key=lambda x:(x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1]))[-1]  # only use the maximum face
            face_emb = face_info['embedding']
            face_kps = draw_kps(conditional_image, face_info['kps'])
            if kwargs.get("kps_conditional_image"):
                conditional_image: Image.Image = self.process_conditional_image(key="kps_conditional_image", resolution=512, **kwargs)
                face_info = app.get(cv2.cvtColor(np.array(conditional_image), cv2.COLOR_RGB2BGR))
                face_info = sorted(face_info, key=lambda x:(x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1]))[-1]  # only use the maximum face
                face_kps = draw_kps(conditional_image, face_info['kps'])
            
            kwargs.update(
                {
                    "image_embeds": face_emb,
                    "image": face_kps,
                    "controlnet_conditioning_scale": controlnet_conditioning_scale,
                    "ip_adapter_scale": ip_adapter_scale,
                }
            )
            images = pipe(*args, **kwargs)
            pipe.set_ip_adapter_scale(0)
            return images

        return inference_function

    def process_conditional_image(self, key="conditional_image", **kwargs) -> Image.Image:
        conditional_image = kwargs[key]
        conditional_image = base64_to_pil_image(conditional_image)
        resolution = kwargs.get("resolution", 1024)
        conditional_image = resize_for_condition_image(conditional_image, resolution)
        return conditional_image

    def padding_to_square(self, image: Image.Image, color = (0,0,0,0)) -> Image.Image:
        width, height = image.size
        if width == height:
            return image
        if width > height:
            new_image = Image.new("RGB", (width, width), color)
            new_image.paste(image, (0, (width - height) // 2))
        else:
            new_image = Image.new("RGB", (height, height), color)
            new_image.paste(image, ((height - width) // 2, 0))
        return new_image

    def load_controlnet_pipeline(self, components, supporting_pipelines) -> callable:
        if "controlnet" not in supporting_pipelines:
            return None
        from controlnet_aux import CannyDetector, AnylineDetector
        anyline = AnylineDetector.from_pretrained(
            "TheMistoAI/MistoLine", filename="MTEED.pth", subfolder="Anyline"
        ).to("cuda")

        controlnet = diffusers.ControlNetModel.from_pretrained(
            "TheMistoAI/MistoLine",
            torch_dtype=torch.float16,
            revision="refs/pr/3",
            variant="fp16",
        )

        canny = CannyDetector()

        controlnet_pipe = diffusers.StableDiffusionXLControlNetPipeline(
            controlnet=controlnet,
            **components,
        )

        controlnet_pipe.to("cuda")

        def inference_function(*args, **kwargs):
            conditional_image = self.process_conditional_image(**kwargs)
            if not kwargs.get("processed", False):
                conditional_image = anyline(conditional_image, detect_resolution=1280, guassian_sigma=kwargs.get("guassian_sigma", 2.0), intensity_threshold=kwargs.get("intensity_threshold", 3.0))
            conditional_image = self.padding_to_square(conditional_image)
            conditional_image = conditional_image.resize((1024, 1024))
            kwargs.update(
                {
                    "image": conditional_image,
                    "width": 1024,
                    "height": 1024
                }
            )
            return controlnet_pipe(*args, **kwargs)

        return inference_function