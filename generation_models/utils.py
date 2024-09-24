from diffusers import (
    EulerDiscreteScheduler,
    EulerAncestralDiscreteScheduler,
    DPMSolverMultistepScheduler,
    LCMScheduler,
)
from io import BytesIO
import base64
import PIL.Image
from PIL import Image
import numpy as np
import requests
import os
from tqdm import tqdm
import io
import importlib
import torch
import bittensor as bt
import random
from generation_models.constant import ASPECT_RATIO_TO_SIZE


def make_inpaint_condition(image, image_mask):
    image = np.array(image.convert("RGB")).astype(np.float32) / 255.0
    image_mask = np.array(image_mask.convert("L")).astype(np.float32) / 255.0

    assert (
        image.shape[0:1] == image_mask.shape[0:1]
    ), "image and image_mask must have the same image size"
    image[image_mask > 0.5] = -1.0  # set as masked pixel
    image = np.expand_dims(image, 0).transpose(0, 3, 1, 2)
    image = torch.from_numpy(image)
    return image


def instantiate_from_config(config):
    if "target" not in config:
        if config == "__is_first_stage__":
            return None
        elif config == "__is_unconditional__":
            return None
        raise KeyError("Expected key `target` to instantiate.")
    return get_obj_from_str(config["target"])(**config.get("params", dict()))


def get_obj_from_str(string, reload=False, invalidate_cache=True):
    module, cls = string.rsplit(".", 1)
    if invalidate_cache:
        importlib.invalidate_caches()
    if reload:
        module_imp = importlib.import_module(module)
        importlib.reload(module_imp)
    return getattr(importlib.import_module(module, package=None), cls)


def set_scheduler(scheduler_name: str, config):
    if scheduler_name == "euler":
        scheduler = EulerDiscreteScheduler.from_config(config)
    elif scheduler_name == "euler_a":
        scheduler = EulerAncestralDiscreteScheduler.from_config(config)
    elif scheduler_name == "dpm++2m_karras":
        scheduler = DPMSolverMultistepScheduler.from_config(
            config, use_karras_sigmas=True
        )
    elif scheduler_name == "dpm++sde_karras":
        scheduler = DPMSolverMultistepScheduler.from_config(
            config,
            algorithm_type="sde-dpmsolver++",
            use_karras_sigmas=True,
        )
    elif scheduler_name == "dpm++2m":
        scheduler = DPMSolverMultistepScheduler.from_config(config)
    elif scheduler_name == "dpm++sde":
        scheduler = DPMSolverMultistepScheduler.from_config(
            config, algorithm_type="sde-dpmsolver++"
        )
    elif scheduler_name == "lcm":
        scheduler = LCMScheduler.from_config(config)
    else:
        raise ValueError(f"Unknown scheduler: {scheduler_name}")

    return scheduler


def base64_to_pil_image(base64_image):
    image = base64.b64decode(base64_image)
    image = BytesIO(image)
    image = PIL.Image.open(image)
    image = image.convert("RGB")
    return image


def pil_image_to_base64(image: Image.Image, format="PNG") -> str:
    if format not in ["JPEG", "PNG"]:
        format = "JPEG"
    image_stream = io.BytesIO()
    image = image.convert("RGB")
    image.save(image_stream, format=format)
    base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")
    return base64_image

def pil_image_to_base64url(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    base64_url = f"data:image/png;base64,{img_str}"
    return base64_url


def resize_divisible(image, max_size=1024, divisible=16):
    W, H = image.size
    if W > H:
        W, H = max_size, int(max_size * H / W)
    else:
        W, H = int(max_size * W / H), max_size
    W = W - W % divisible
    H = H - H % divisible
    image = image.resize((W, H))
    return image


def resize_for_condition_image(input_image: Image, resolution: int):
    input_image = input_image.convert("RGB")
    W, H = input_image.size
    k = float(resolution) / min(H, W)
    H *= k
    W *= k
    H = int(round(H / 64.0)) * 64
    W = int(round(W / 64.0)) * 64
    img = input_image.resize((W, H), resample=Image.LANCZOS)
    return img


def download_checkpoint(download_url, checkpoint_file):
    folder, filename = os.path.split(checkpoint_file)
    os.makedirs(folder, exist_ok=True)
    with requests.get(download_url, stream=True) as response:
        total_size = int(response.headers.get("content-length", 0))
        with open(checkpoint_file, "wb") as file_stream, tqdm(
            desc=checkpoint_file,
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for data in response.iter_content(chunk_size=1024):
                file_stream.write(data)
                progress_bar.update(len(data))

    bt.logging.info("Download completed successfully.")


def upscale_image(input_image, upscale, max_size_input=None):
    import cv2

    H, W, C = input_image.shape
    H = float(H)
    W = float(W)
    k = float(max_size_input) / max(H, W)
    H *= k
    W *= k
    H = int(np.round(H / 64.0)) * 64
    W = int(np.round(W / 64.0)) * 64
    H *= upscale
    W *= upscale
    img = cv2.resize(
        input_image,
        (W, H),
        interpolation=cv2.INTER_LANCZOS4 if upscale > 1 else cv2.INTER_AREA,
    )
    img = img.round().clip(0, 255).astype(np.uint8)
    return img


def resize_image(input_image, resolution, short=False, interpolation=None):
    W, H = input_image.size

    H = float(H)
    W = float(W)
    if short:
        k = float(resolution) / min(H, W)  # k>1 放大， k<1 缩小
    else:
        k = float(resolution) / max(H, W)  # k>1 放大， k<1 缩小
    H *= k
    W *= k
    H = int(np.round(H / 64.0)) * 64
    W = int(np.round(W / 64.0)) * 64

    if interpolation is None:
        interpolation = PIL.Image.LANCZOS if k > 1 else PIL.Image.BILINEAR
    img = input_image.resize((W, H), resample=interpolation)

    return img


def random_image_size():
    aspect_ratio = random.choice(list(ASPECT_RATIO_TO_SIZE.keys()))
    width, height = ASPECT_RATIO_TO_SIZE[aspect_ratio]
    return width, height


def convert_image_to_png_format(image):
    png_image_io = io.BytesIO()
    image.save(png_image_io, format="PNG")
    png_image_io.seek(0)
    png_image = Image.open(png_image_io)
    return png_image
