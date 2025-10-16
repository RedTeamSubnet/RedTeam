import os
import uvicorn
from fastapi import FastAPI
import logging

logger = logging.getLogger()
app = FastAPI()


@app.get("/ping")
def ping():
    return {"status": "ok", "process_id": os.getpid()}


def start_ping_server(port: int = 8000):
    logger.info(f"Starting ping server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
