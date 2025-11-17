# -*- coding: utf-8 -*-

import sys
import logging
import pathlib

from fastapi import FastAPI, Body, HTTPException
from data_types import MinerInput, MinerOutput


logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S %z",
    format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
)


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve", response_model=MinerOutput)
def solve(miner_input: MinerInput = Body(...)) -> MinerOutput:

    logger.info(f"Retrieving detection.js and related files...")
    _miner_output: MinerOutput
    try:
        _src_dir = pathlib.Path(__file__).parent.resolve()
        _detection_dir = _src_dir / "detections"
        # get all js script in dectection folder
        _detection_js_files = list(_detection_dir.glob("*.js"))

        _detection_files = {}
        for js_file in _detection_js_files:
            with open(js_file, "r") as file:
                _detection_files[js_file.name] = file.read()

        _miner_output = MinerOutput(
            detection_js=_detection_files,
        )
        logger.info(f"Successfully retrieved detection.js and related files.")
    except Exception as err:
        logger.error(f"Failed to retrieve detection.js and related files: {err}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve detection.js and related files."
        )

    return _miner_output


___all___ = ["app"]
