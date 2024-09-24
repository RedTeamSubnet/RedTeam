from image_generation_subnet.protocol import ImageGenerating
import random
import requests
import os
import numpy as np
import bittensor as bt
from PIL import Image
from generation_models.utils import (
    pil_image_to_base64, 
    pil_image_to_base64url
)


def get_promptGoJouney(synapses: list[ImageGenerating]) -> list[ImageGenerating]:
    ars = [
        "16:9",
        "1:1",
        "9:16",
        "4:5",
        "5:4",
        "3:4",
        "4:3",
        "2:3",
        "3:2",
    ]
    synapses = check_batch_prompt(synapses)
    for synapse in synapses:
        if not synapse:
            continue
        synapse.prompt = f"{synapse.prompt} --ar {random.choice(ars)} --v 6"
    return synapses


def check_a_prompt(prompt: str) -> str:
    endpoint = "https://api.midjourneyapi.xyz/mj/v2/validation"
    data = {"prompt": prompt}
    response = requests.post(endpoint, json=data, timeout=10)
    response = response.json()
    return response["ErrorMessage"]


def get_offline_prompt():
    landscapes = ["landscape", "mountain", "forest", "beach", "desert", "city"]
    animals = ["dog", "cat", "bird", "fish", "horse", "rabbit"]
    actions = ["running", "jumping", "flying", "swimming", "sitting", "standing"]
    return f"{random.choice(landscapes)} with {random.choice(animals)} {random.choice(actions)}, {random.randint(1, 10000)}"


def get_backup_prompt():
    return {"prompt": get_offline_prompt()}

def get_backup_llm_prompt():
    return {
        "prompt_input": "How AI can change the world?",
        "pipeline_params": {
            "max_tokens": 1024,
            "logprobs": 100,
        },
    }


def get_backup_image():
    blank_image = Image.new("RGB", (512, 512), "white")
    return {"conditional_image": pil_image_to_base64(blank_image)}

def interpolate_images():
    image_dir = "assets/images"
    image_files = [os.path.join(image_dir,x) for x in os.listdir(image_dir)]
    
    img_file_1, img_file_2 = random.sample(image_files, 2)
    img_1, img_2 = Image.open(img_file_1), Image.open(img_file_2)
    img_1 = img_1.convert("RGBA")
    img_2 = img_2.convert("RGBA")
    img_1 = img_1.resize(img_2.size)
    
    sigma = np.random.rand()
    
    challenge_image = Image.blend(img_1, img_2, alpha=sigma)

    return challenge_image

def get_backup_challenge_vqa():
    questions = ["Describe in detail what is happening in this image, including objects, actions, and context. Make sure to provide a comprehensive description that captures all visible elements.", "Describe this image in a short sentence"]
    question = random.choice(questions)

    init_image = interpolate_images()
    return {
        "prompt": question,
        "image_url": pil_image_to_base64url(init_image)
    }
def check_batch_prompt(synapses: list[ImageGenerating]) -> list[ImageGenerating]:
    for synapse in synapses:
        if not synapse:
            continue
        if check_a_prompt(synapse.prompt):
            synapse.prompt = get_offline_prompt()
            bt.logging.warning(
                f"Prompt {synapse.prompt} is not valid, use offline prompt: {synapse.prompt}"
            )
    return synapses
