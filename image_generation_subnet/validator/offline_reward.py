from image_generation_subnet.protocol import ImageGenerating
import requests
import bittensor as bt
import re
from diffusers.utils import load_image
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import torch
from image_generation_subnet.utils.moderation_model import Moderation
import bittensor as bt

URL_REGEX = (
    r"https://(?:oaidalleapiprodscus|dalleprodsec)\.blob\.core\.windows\.net/private/org-[\w-]+/"
    r"user-[\w-]+/img-[\w-]+\.(?:png|jpg)\?"
    r"st=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&"
    r"se=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&"
    r"(?:sp=\w+&)?"
    r"sv=\d{4}-\d{2}-\d{2}&"
    r"sr=\w+&"
    r"rscd=\w+&"
    r"rsct=\w+/[\w-]+&"
    r"skoid=[\w-]+&"
    r"sktid=[\w-]+&"
    r"skt=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&"
    r"ske=\d{4}-\d{2}-\d{2}T\d{2}%3A\d{2}%3A\d{2}Z&"
    r"sks=\w+&"
    r"skv=\d{4}-\d{2}-\d{2}&"
    r"sig=[\w/%+=]+"
)

# Dall E
# model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
# processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
MODEL = None
PROCESSOR = None
# Moderation

moderation_model = None


def fetch_GoJourney(task_id):
    endpoint = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {"task_id": task_id}
    response = requests.post(endpoint, json=data)
    return response.json()


def get_reward_GoJourney(
    base_synapse: ImageGenerating,
    synapses: list[ImageGenerating],
    uids: list,
    *args,
    **kwargs,
) -> list[float]:
    reward_distribution = {
        "turbo": 1.0,
        "fast": 0.5,
        "relax": 0.1,
    }
    rewards = []
    prompt = base_synapse.prompt
    for synapse in synapses:
        try:
            synapse_response: dict = synapse.response_dict
            bt.logging.info(synapse_response)
            task_id = synapse_response["task_id"]
            task_response = fetch_GoJourney(task_id)
            task_request = task_response["meta"]["task_request"]
            task_status = task_response["status"]
            bt.logging.info(f"Synapse base: {base_synapse}")
            bt.logging.info(f"Task status: {task_status}")
            bt.logging.info(f"Task request: {task_request}")
            bt.logging.info(f"Task response: {task_response}")
            if task_status == "failed":
                bt.logging.info("Task failed")
                reward = 0
            elif (
                task_request["prompt"].split("--")[0].strip()
                != prompt.split("--")[0].strip()
            ):
                bt.logging.info(
                    f"Prompt mismatch: {task_request['prompt']} != {prompt}"
                )
                reward = 0
            else:
                process_mode = task_response["meta"]["task_request"]["process_mode"]
                reward = reward_distribution[process_mode]
                bt.logging.info(f"Process_mode: {process_mode}")
            rewards.append(reward)
        except Exception as e:
            bt.logging.warning(f"Error in get_reward_GoJourney: {e}")
            rewards.append(0)
    return uids, rewards


def calculate_image_similarity(image, description, max_length: int = 77):
    """Calculate the cosine similarity between a description and an image."""
    # Truncate the description
    inputs = processor(
        text=description,
        images=None,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length,
    )
    text_embedding = model.get_text_features(**inputs)

    # Process the image
    inputs = processor(
        text=None, images=image, return_tensors="pt", padding=True, truncation=True
    )
    image_embedding = model.get_image_features(**inputs)

    # Calculate cosine similarity
    return torch.cosine_similarity(image_embedding, text_embedding, dim=1).item()


def get_reward_dalle(
    base_synapse: ImageGenerating,
    synapses: list[ImageGenerating],
    uids: list,
    similarity_threshold=0.25,
    *args,
    **kwargs,
) -> float:
    """Calculate the image score based on similarity and size."""
    global MODEL
    global PROCESSOR

    if MODEL is None:
        MODEL = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
    if PROCESSOR is None:
        PROCESSOR = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
    global moderation_model
    if moderation_model is None:
        moderation_model = Moderation()

    rewards = []
    prompt = base_synapse.prompt

    flagged, response = moderation_model(prompt)
    if flagged:
        bt.logging.debug(prompt)
        bt.logging.debug(response)
        return uids, [1] * len(synapses)

    def check_size(size):
        return size in ["1792x1024", "1024x1792"]

    def check_regex(url):
        return re.match(URL_REGEX, url)

    for synapse in synapses:
        try:
            bt.logging.debug(synapse.response_dict)
            bt.logging.debug(synapse.prompt)
            response = synapse.response_dict
            url = response.get("url", "")
            prompt = base_synapse.prompt
            image: Image.Image = load_image(url)
            size_str = f"{image.width}x{image.height}"
            sim = calculate_image_similarity(image, prompt)
            bt.logging.info(f"CLIP Similarity DallE: {sim}")
            if sim > similarity_threshold:
                max_reward = 1
            elif 0.15 < sim < similarity_threshold:
                max_reward = sim / similarity_threshold
            else:
                max_reward = 0.0

            if check_size(size_str) and check_regex(url):
                rewards.append(max_reward)
            else:
                rewards.append(0)
        except Exception as e:
            bt.logging.warning(f"Error in get_reward_dalle: {e}")
            rewards.append(0)

    return uids, rewards
