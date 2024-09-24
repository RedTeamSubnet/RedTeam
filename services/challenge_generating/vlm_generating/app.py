"""
Synthetic Prompt Generation Service for the Visual Language Modeling Challenge.
```bash
uvicorn app:app.app
```
"""

from datasets import load_dataset
from fastapi import FastAPI
import random
import httpx


class VLMSyntheticPrompt:
    """
    A FastAPI-based service for retrieving synthetic prompts from the LAION high-resolution dataset.
    The class loads a dataset of high-resolution images and serves valid image URLs with prompts via a POST request.
    """

    def __init__(self):
        """
        Initializes the FastAPI app and loads the LAION high-resolution dataset.
        Sets up the API route for POST requests.
        """
        self.app = FastAPI()
        self.app.add_api_route("/", self.__call__, methods=["POST"])
        self.dataset = self.load_dataset()

    def load_dataset(self):
        """
        Loads the LAION high-resolution dataset from Hugging Face Datasets.
        The dataset is cached locally and shuffled after loading.

        Returns:
            Dataset: The shuffled LAION high-resolution dataset.
        """
        dataset = load_dataset(
            "laion/laion-high-resolution",
            split="train",
            num_proc=4,
        )
        dataset = dataset.shuffle()
        return dataset

    async def _get_valid_item(self):
        """
        Retrieves a valid item from the dataset by randomly selecting an image and validating the URL.

        The function attempts to retrieve a valid item from the dataset up to 10 times.
        If no valid item is found after 10 tries, it returns None.

        Returns:
            dict: A valid dataset item (if found) or None.
        """
        i = 0
        while True:
            item = self.dataset[random.randint(0, len(self.dataset) - 1)]
            image_url = item["URL"]
            is_valid = await self.verify_image_url(image_url)
            if is_valid:
                return item
            i += 1
            if i > 10:
                return None

    @staticmethod
    async def verify_image_url(image_url):
        """
        Verifies if the given image URL points to a valid image format (PNG, JPEG, JPG, WEBP).

        Args:
            image_url (str): The image URL to be verified.

        Returns:
            bool: True if the URL is valid and points to an image, otherwise False.
        """
        try:
            image_formats = ("image/png", "image/jpeg", "image/jpg", "image/webp")
            async with httpx.AsyncClient(timeout=1) as client:
                r = await client.head(image_url)
            if r.headers["content-type"] in image_formats:
                return True
            return False
        except Exception as e:
            return False

    async def __call__(self, data={}):
        """
        API endpoint handler for retrieving a valid image URL and generating a synthetic prompt.

        Args:
            data (dict): Input data for the API request (default: {}).

        Returns:
            dict: A dictionary containing the valid image URL and a synthetic prompt description.
        """
        item = await self._get_valid_item()
        if not item:
            return {"error": "No valid image found"}

        image_url = item["URL"]
        return {
            "image_url": image_url,
            "prompt": "Describe the image in details.",
        }


app = VLMSyntheticPrompt()
