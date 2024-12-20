import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MAX_MAX_NEW_TOKENS = 2048
DEFAULT_MAX_NEW_TOKENS = 1024
MAX_INPUT_TOKEN_LENGTH = int(os.getenv("MAX_INPUT_TOKEN_LENGTH", "4096"))


class MyModel():
    def __init__(self, model_id = "unsloth/Llama-3.2-3B-Instruct") -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
        ).to(self.device)
        self.model.eval()

    def generate(
        self,
        message: str,
        chat_history: list[tuple[str, str]] = [],
        max_new_tokens: int = 10,
        temperature: float = 0.6,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.2,
    ):
        conversation = []
        for user, assistant in chat_history:
            conversation.extend(
                [
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            )
        conversation.append({"role": "user", "content": message})

        input_ids = self.tokenizer.apply_chat_template(conversation, add_generation_prompt=True, return_tensors="pt")
        if input_ids.shape[1] > MAX_INPUT_TOKEN_LENGTH:
            input_ids = input_ids[:, -MAX_INPUT_TOKEN_LENGTH:]
            print(f"Trimmed input from conversation as it was longer than {MAX_INPUT_TOKEN_LENGTH} tokens.")
        input_ids = input_ids.to(self.device)

        generate_kwargs = dict(
            {"input_ids": input_ids},
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            num_beams=1,
            repetition_penalty=repetition_penalty,
        )
        outputs = self.model.generate(**generate_kwargs)
        response =  self.tokenizer.decode(outputs[0][len(input_ids[0]):], skip_special_tokens=True)
        return response
