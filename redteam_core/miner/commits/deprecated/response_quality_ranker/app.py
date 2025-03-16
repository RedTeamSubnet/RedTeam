from fastapi import FastAPI
from model import ResponseQualityHandler
from data_types import MinerInput, MinerOutput

app = FastAPI()
model = ResponseQualityHandler()

@app.post("/solve")
async def solve(data: MinerInput):
    payload = {
        'inputs': [
            {
                "instruction": data.prompt,
                "response": response
            } for response in data.responses
        ]
    }
     
    response_quality = [x["response_quality"] for x in model(payload)]
    return MinerOutput(
        response_quality=response_quality
    )

@app.get("/health")
def health():
    return {"status": "ok"}
