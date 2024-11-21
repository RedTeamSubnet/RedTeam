from fastapi import FastAPI
import random
from data_types import MinerInput, MinerOutput

app = FastAPI()
LENGTH = 1000


@app.post("/solve")
def solve(data: MinerInput):
    return MinerOutput(
        text="".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=LENGTH))
    )


@app.get("/health")
def health():
    return {"status": "ok"}
