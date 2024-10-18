from fastapi import FastAPI
import random
from data_types import MinerInput, MinerOutput

app = FastAPI()
LENGTH = 1000


@app.get("/solve")
def solve(data: MinerInput):
    return MinerOutput(
        text="".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=LENGTH))
    )
