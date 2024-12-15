from fastapi import FastAPI
from data_types import MinerInput, MinerOutput
from bot import WebUIAutomate

app = FastAPI()
automator = WebUIAutomate(username="username", password="password")


@app.post("/solve")
async def solve(data: MinerInput) -> MinerOutput:
    result = automator(data)
    if not result:
        return MinerOutput(
            ciphertext="",
            key="",
            iv="",
        )
    return MinerOutput(
        ciphertext=result.ciphertext,
        key=result.key,
        iv=result.iv,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
