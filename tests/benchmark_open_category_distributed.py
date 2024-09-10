import image_generation_subnet as ig
import requests
from generation_models.utils import base64_to_pil_image

synapse = ig.protocol.ImageGenerating(model_name="OpenCategory", timeout=12)

sample_prompts = [
    "a cat is sitting on a chair, behind is a window with a view of a garden.",
    "a landscape photo of a large, open field with a clear blue sky. In the distance, a small group of trees can be seen, and a mountain range is visible on the horizon. The sun is shining brightly, casting long shadows on the ground.",
    "a photo of a young man with a serious expression. He has short, dark hair and is wearing a light-colored, long-sleeved shirt with a collar.",
    "A bustling marketplace scene unfolds under a clear blue sky. At the center, a vendor with a bright red apron is enthusiastically showcasing a variety of fresh fruits and vegetables arranged neatly on a wooden stall. To the left, a small child, wearing a blue cap, reaches up with a curious smile to grab an apple, while her mother, in a floral dress, gently guides her hand. Nearby, an elderly man with a cane, sporting a straw hat, leans over to inspect a basket of ripe tomatoes.",
]

from services.rewarding.open_category_reward import OpenCategoryReward

rewarder = OpenCategoryReward()

for i, prompt in enumerate(sample_prompts):
    print("Prompt: ", prompt)
    synapse.prompt = prompt
    synapse.pipeline_params = {
        "width": 1024,
        "height": 1024,
        "num_inference_steps": 30,
    }
    response = requests.post(
        "http://localhost:10006/generate", json=synapse.deserialize_input()
    )
    response.raise_for_status()
    response = response.json()
    image = base64_to_pil_image(response["image"])
    image.save(f"tmp_{i}.png")
    print("Image saved to tmp.png")
    reward = rewarder.get_reward(prompt, [response["image"]], store=False)
    print(reward)
