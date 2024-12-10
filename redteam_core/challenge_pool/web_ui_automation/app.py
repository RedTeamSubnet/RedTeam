from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from challenge import Challenge
from data_types import MinerInput, MinerOutput

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
challenge = Challenge()

@app.get("/task")
def get_task(request: Request):
    is_validator = request.headers.get('X-Validator-Token') is not None
    return challenge.prepare_task(is_validator)

@app.post("/score")
async def score(request: Request):
    data = await request.json()
    miner_output = MinerOutput(**data)
    score = challenge.score_task(
        miner_input=request.state.miner_input,
        miner_output=miner_output
    )
    return {"score": score}

@app.get("/health")
def health():
    return {"status": "healthy"}