# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import pathlib
import requests
from typing import Union, List

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import JSONResponse
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


@app.get("/test-script")
def test_script() -> float:
    try:
        # Test ESLint first
        eslint_response = test_eslint()
        eslint_data = eslint_response.body.decode("utf-8")
        eslint_json = json.loads(eslint_data)

        if not eslint_json.get("passed", False):
            error_msg = eslint_json.get("message", "ESLint check failed")
            logger.error(f"ESLint check failed: {error_msg}")
            return eslint_response

        # Proceed with miner test only if ESLint passes
        miner_input = {"random_val": "a1b2c3d4e5f6g7h8"}
        miner_output: MinerOutput = solve(miner_input=miner_input)
        response = requests.post(
            "http://localhost:10001/score",
            json={
                "miner_input": miner_input,
                "miner_output": miner_output.model_dump(),
            },
        )

        score = response.json()
        if not isinstance(score, (int, float)):
            logger.error(f"Expected numeric score, got: {type(score)}")
            raise HTTPException(
                status_code=500, detail="Score service returned non-numeric value"
            )

        logger.info(f"Received Score: {score}")
        return score

    except Exception as err:
        logger.error(f"Failed to retrieve score: {err}")
        raise HTTPException(status_code=500, detail="Failed to retrieve score")


@app.get("/test-eslint")
def test_eslint() -> JSONResponse:
    try:
        response = requests.post(
            "http://localhost:10001/eslint-check",
            timeout=60,
            json={
                "js_content": _load_detection_js(),
            },
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)

    except Exception as e:
        logger.error(f"Failed to test ESLint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test ESLint: {e}")


def _load_detection_js() -> str:
    try:
        _src_dir = pathlib.Path(__file__).parent.resolve()
        _detection_dir = _src_dir / "detection"
        _detection_js_path = str(_detection_dir / "detection.js")
        with open(_detection_js_path, "r") as _detection_js_file:
            return _detection_js_file.read()
    except Exception as e:
        logger.error(f"Failed to load detection.js: {e}")
        raise HTTPException(status_code=500, detail="Failed to load detection.js")


@app.post("/solve", response_model=MinerOutput)
def solve(miner_input: MinerInput = Body(...)) -> MinerOutput:

    logger.info(f"Retrieving detection.js and related files...")
    _miner_output: MinerOutput
    try:
        _src_dir = pathlib.Path(__file__).parent.resolve()
        _detection_dir = _src_dir / "detection"

        _detection_js_path = str(_detection_dir / "detection.js")
        _detection_js = (
            "function detectDriver() { localStorage.setItem('driver', 'Chrome'); }"
        )
        with open(_detection_js_path, "r") as _detection_js_file:
            _detection_js = _detection_js_file.read()

        # _requirements_txt_path = str(_detection_dir / "requirements.txt")
        # _pip_requirements: Union[List[str], None] = None
        # if os.path.exists(_requirements_txt_path):
        #     with open(_requirements_txt_path, "r") as _requirements_txt_file:
        #         _pip_requirements = [_line.strip() for _line in _requirements_txt_file]

        # _system_deps_path = str(_detection_dir / "system_deps.txt")
        # _system_deps: Union[str, None] = None
        # if os.path.exists(_system_deps_path):
        #     with open(_system_deps_path, "r") as _system_deps_file:
        #         _system_deps = _system_deps_file.read()
        #         if _system_deps:
        #             _system_deps = None

        _miner_output = MinerOutput(
            detection_js=_detection_js,
            # system_deps=_system_deps,
            # pip_requirements=_pip_requirements,
        )
        logger.info(f"Successfully retrieved detection.js and related files.")
    except Exception as err:
        logger.error(f"Failed to retrieve detection.js and related files: {err}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve detection.js and related files."
        )

    return _miner_output


___all___ = ["app"]
