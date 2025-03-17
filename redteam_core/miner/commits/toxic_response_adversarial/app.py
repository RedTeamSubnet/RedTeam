import json
import random
from fastapi import FastAPI
from data_types import MinerInput, MinerOutput

app = FastAPI()

# Read the prepared adversarial prompts from the file
with open("adversarial_prompts.json", "r") as file:
    adversarial_prompts = json.load(file)

@app.post("/solve")
async def solve(data: MinerInput):
    output_num = data.output_num
    # Chose random adversarial prompts
    random_adversarial_prompts = random.sample(adversarial_prompts, output_num)
    return MinerOutput(
        adversarial_prompts=random_adversarial_prompts
    )

@app.get("/health")
def health():
    return {"status": "ok"}
