from fastapi import FastAPI
from model import MyModel
from data_types import MinerInput, MinerOutput

app = FastAPI()
llm = MyModel()

@app.post("/solve")
async def solve(data: MinerInput):
    response = llm.generate(message=data.modified_prompt)
    return MinerOutput(
        response=response
    )

@app.get("/health")
def health():
    return {"status": "ok"}

