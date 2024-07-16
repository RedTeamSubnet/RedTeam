from .base_model import BaseModel
import random
from openai import OpenAI, AsyncOpenAI
from image_generation_subnet.utils.moderation_model import Moderation
import asyncio
import bittensor as bt

SAFE_TEMPLATE = "please remove not safe for work contents and revise this input prompt to a safe for work prompt.\n Input prompt: {}"


class NicheDallE(BaseModel):
    def __init__(self, *args, **kwargs):
        self.inference_function = self.load_model(*args, **kwargs)
        self.client = AsyncOpenAI()
        self.moderation = Moderation()

    def load_model(self, *args, **kwargs):
        imagine_inference_function = self.load_imagine(*args, **kwargs)
        return imagine_inference_function

    def __call__(self, *args, **kwargs):
        return self.inference_function(*args, **kwargs)

    async def check_safety(self, prompt):
        response = await self.client.moderations.create(input=prompt)
        output = response.results[0]
        is_flagged = output.flagged
        return is_flagged

    def load_imagine(self, *args, **kwargs):
        supporting_sizes = ["1792x1024", "1024x1792"]

        def inference_function(*args, **kwargs):
            prompt = kwargs.get("prompt", "a cute cat")
            # check prompt safety
            flagged, response = self.moderation(prompt)
            if flagged:
                bt.logging.info(response)
                data = {
                    "url": "",
                    "revised_prompt": "",
                    "flagged": (True, response),
                }
            else:
                bt.logging.info("Prompt is safe for work - Offline Moderation")
                is_openai_flagged = asyncio.get_event_loop().run_until_complete(
                    self.check_safety(prompt)
                )
                if is_openai_flagged:
                    prompt = SAFE_TEMPLATE.format(prompt)
                    bt.logging.info(f"Adding safe prompt template: {prompt}")
                else:
                    bt.logging.info("Prompt is safe for work - OpenAI Moderation")
                style = kwargs.get("style", "natural")
                if style not in ["vivid", "natural"]:
                    style = "natural"
                size = kwargs.get("size", random.choice(supporting_sizes))
                if size not in supporting_sizes:
                    size = random.choice(supporting_sizes)
                loop = asyncio.get_event_loop()

                def _generate(prompt, size, style):
                    response_obj = loop.run_until_complete(
                        self.client.images.generate(
                            model="dall-e-3",
                            prompt=prompt,
                            n=1,
                            size=size,
                            response_format="url",
                            style=style,
                        )
                    )
                    data = {
                        "url": response_obj.data[0].url,
                        "revised_prompt": response_obj.data[0].revised_prompt,
                    }
                    return data

                try:
                    data = _generate(prompt, size, style)
                except Exception as e:
                    bt.logging.error(f"Error: {e}")
                    prompt = SAFE_TEMPLATE.format(prompt)
                    bt.logging.info(f"Retrying with safe prompt: {prompt}")
                    data = _generate(prompt, size, style)

            bt.logging.info(data)
            return data

        return inference_function
