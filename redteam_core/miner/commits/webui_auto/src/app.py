import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Body
from data_types import MinerInput, MinerOutput
from bot import WebUIAutomate
from dependency import get_webui_automate


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.
    Startup and shutdown events are logged.

    Args:
        app (FastAPI, required): FastAPI application instance.
    """

    logging.info("Preparing to startup...")
    get_webui_automate()
    logging.info("Finished preparation to startup.")

    yield

    logging.info("Praparing to shutdown...")
    get_webui_automate().cleanup()
    logging.info("Finished preparation to shutdown.")


app = FastAPI(lifespan=lifespan)


@app.post("/solve")
def solve(
    miner_input: MinerInput = Body(...),
    automator: WebUIAutomate = Depends(get_webui_automate),
) -> MinerOutput:

    result = automator(miner_input)

    return MinerOutput(
        ciphertext=result.ciphertext,
        key=result.key,
        iv=result.iv,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
