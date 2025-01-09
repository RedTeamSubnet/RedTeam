from data_types import MinerInput, MinerOutput
from model import ResponseQualityHandler
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np
import random
import os
import openai
class Challenge:
    """
    A class that sets up the challenge and scores the miner's performance.
    It provides the task to be completed and evaluates the output.
    """
    def __init__(self):
        self.model = ResponseQualityHandler()
        VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8000/v1") 
        VLLM_API_KEY = os.environ.get("API_KEY", "api-key")
        self.model_name = os.environ.get("VLLM_MODEL", "unsloth/Meta-Llama-3.1-8B-Instruct")
        self.client = openai.OpenAI(
            base_url=VLLM_URL,
            api_key=VLLM_API_KEY,
        )

        with open("questions.txt") as f:
            self.questions = f.readlines()

        self.stop_words = set(stopwords.words('english'))
        
    def prepare_task(self) -> MinerInput:
        """
        Prepares the task by returning an instance of MinerInput,
        which contains the task description.
        """
        original_prompt = random.choice(self.questions)
        rephrased_prompt = self._rephrase_question(original_prompt)
        modified_prompt = self._generate_modified_prompt(rephrased_prompt)
        return MinerInput(original_prompt=rephrased_prompt, modified_prompt=modified_prompt)

    def score_task(self, miner_input: MinerInput, miner_output: MinerOutput) -> float:
        """
        Evaluates the output generated by the miner.
        """

        payload = {
            'inputs': [
                {
                    "instruction": miner_input.original_prompt,
                    "response": miner_output.response
                },
            ]
        }
        score = self.model(payload)[0]["response_quality"]

        return score

    def _rephrase_question(self, original_prompt: str) -> str:
        PROMPT_REPHRASE = f"""Original question: {original_prompt}
Please rewrite this question freely to make it as difficult as possible for search algorithms to match. You can rephrase, alter the context, use indirect phrasing, or break it into multiple parts, as long as the core meaning is preserved. 

Return only the modified question without any explanation."
""" 
        messages = [
            {"role": "user", "content": PROMPT_REPHRASE}
        ]
        try:
            response = self._call_vllm(messages)
            return response
        except Exception as e:
            print(f"[REPHRASE] Failed to rephrase the question: {e}")
            return original_prompt

    def _generate_modified_prompt(self, original_prompt: str) -> str:
        """
        Generates a modified version of the original prompt by masking a key term.
        """
        words = word_tokenize(original_prompt)
        stop_word_indices = [i for i, word in enumerate(words) if word.lower() in self.stop_words]
        total_words = len(words) - len(stop_word_indices)
        num_to_mask = max(1, int(total_words * 0.5)) 

        mask_indices = random.sample(
            [i for i in range(total_words) if i not in stop_word_indices],
            min(num_to_mask, total_words - len(stop_word_indices))
        )
        modified_prompt = " ".join(
            "BLANK" if i in mask_indices else word for i, word in enumerate(words)
        )

        return modified_prompt

    def _call_vllm(self, messages):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=1024,
        )
        print(response)
        content = response.choices[0].message.content
        return content
if __name__ == "__main__":
    challenge = Challenge()
    print(challenge.prepare_task())