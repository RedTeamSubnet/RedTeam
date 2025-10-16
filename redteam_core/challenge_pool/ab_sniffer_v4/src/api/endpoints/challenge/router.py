# -*- coding: utf-8 -*-

import pathlib
from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse

from api.endpoints.challenge.schemas import MinerInput, MinerOutput
from api.endpoints.challenge import service
from api.logger import logger
from pydantic import BaseModel

import os
import json
import subprocess

router = APIRouter(tags=["Challenge"])


@router.get(
    "/task",
    summary="Get task",
    description="This endpoint returns the task for the miner.",
    response_class=JSONResponse,
    response_model=MinerInput,
)
def get_task(request: Request):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting task...")

    _miner_input: MinerInput
    try:
        _miner_input = service.get_task()

        logger.success(f"[{_request_id}] - Successfully got the task.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to get task!",
        )
        raise

    return _miner_input


@router.post(
    "/score",
    summary="Score",
    description="This endpoint score miner output.",
    response_class=JSONResponse,
    responses={400: {}, 422: {}},
)
def post_score(
    request: Request,
    miner_input: MinerInput,
    miner_output: MinerOutput,
):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Evaluating the miner output...")

    _score: float = 0.0
    try:

        _score = service.score(miner_output=miner_output)

        logger.success(f"[{_request_id}] - Successfully evaluated the miner output.")
    except Exception as err:
        if isinstance(err, HTTPException):
            # raise
            logger.error(
                f"[{_request_id}] - Failed to evaluate the miner output!",
            )

        logger.error(
            f"[{_request_id}] - Failed to evaluate the miner output!",
        )
        # raise
        return None
    logger.success(f"[{_request_id}] - Successfully scored the miner output: {_score}")
    return _score


@router.get(
    "/_web",
    summary="Serves the webpage",
    description="This endpoint serves the webpage for the challenge.",
    response_class=HTMLResponse,
    responses={429: {}},
)
def _get_web(request: Request):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting webpage...")

    _html_response: HTMLResponse
    try:
        _html_response = service.get_web(request=request)

        logger.success(f"[{_request_id}] - Successfully got the webpage.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to get the webpage!",
        )
        raise

    return _html_response


@router.post(
    "/human-score",
    description="This endpoint posts the human score.",
    responses={422: {}},
)
def post_human_score(
    request: Request,
    driver: str = Body(..., embed=False),
):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Posting human score...")
    try:
        service.post_human_score(driver, _request_id)
        logger.success(f"[{_request_id}] - Successfully posted human score.")
    except Exception as err:
        logger.error(f"[{_request_id}] - Error posting human score: {str(err)}")
        raise HTTPException(status_code=500, detail="Error in posting human score")

    return


@router.get("/results", response_class=JSONResponse)
def get_results(request: Request):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting results...")
    try:
        results = service.get_results()
        logger.success(f"[{_request_id}] - Successfully got results.")
    except Exception as err:
        logger.error(f"[{_request_id}] - Error getting results: {str(err)}")
        raise HTTPException(status_code=500, detail="Error in getting results")

    return JSONResponse(content=results)


@router.post(
    "/compare",
    summary="Compare miner outputs",
    description="This endpoint compares a miner's output to a reference output.",
    responses={422: {}, 500: {}},
)
def post_compare(
    request: Request,
    miner_output: dict = Body(...),
    reference_output: dict = Body(...),
    miner_input: dict = Body(...),
):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Comparing miner outputs...")

    try:
        _score = service.compare_outputs(
            miner_input=miner_input,
            miner_output=miner_output,
            reference_output=reference_output,
        )
        logger.success(f"[{_request_id}] - Successfully compared miner outputs.")
    except Exception as err:
        logger.error(f"[{_request_id}] - Error comparing miner outputs: {str(err)}")
        raise HTTPException(status_code=500, detail="Error in comparison request")

    return _score


class ESLintRequest(BaseModel):
    js_content: str

    class Config:
        json_schema_extra = {
            "example": {
                "js_content": "// Your JavaScript detection code here\nconsole.log('Hello World');"
            }
        }


@router.post(
    "/eslint-check",
    summary="ESLint check",
    description="This endpoint checks if the provided JavaScript content passes ESLint checks.",
    responses={422: {}, 500: {}},
)
def eslint_check(request: Request, eslint_request: ESLintRequest) -> JSONResponse:
    detection_file = os.path.join(
        "/",
        "app",
        "rest.rt-abs-challenger",
        "templates",
        "static",
        "detection",
        "detection.js",
    )

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(detection_file), exist_ok=True)

        # Write the JavaScript content to the file
        with open(detection_file, "w", encoding="utf-8") as f:
            f.write(eslint_request.js_content)

        logger.info(
            f"[{request.state.request_id}] - Written JavaScript content to {detection_file}"
        )

        cmd = ["npx", "eslint", "--format", "json", detection_file]

        logger.info(f"[{request.state.request_id}] - Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )

        # Handle case where ESLint output might be empty or malformed
        if not result.stdout.strip():
            logger.warning(f"[{request.state.request_id}] - ESLint produced no output")
            return JSONResponse(
                {
                    "passed": False,
                    "message": "ESLint produced no output - possible syntax error",
                    "errors": 1,
                    "warnings": 0,
                    "details": [{"message": "No ESLint output - check syntax"}],
                }
            )

        lint_result = json.loads(result.stdout)
        error_count = lint_result[0].get("errorCount", 0)
        warning_count = lint_result[0].get("warningCount", 0)

        if error_count > 0:
            logger.warning(
                f"[{request.state.request_id}] - ESLint found {error_count} errors"
            )
            return JSONResponse(
                {
                    "passed": False,
                    "message": f"ESLint found {error_count} errors, {warning_count} warnings",
                    "errors": error_count,
                    "warnings": warning_count,
                    "details": lint_result[0].get("messages", []),
                }
            )

        logger.success(f"[{request.state.request_id}] - ESLint passed")
        return JSONResponse(
            {
                "passed": True,
                "message": "ESLint check passed",
                "errors": 0,
                "warnings": warning_count,
            }
        )

    except json.JSONDecodeError as e:
        logger.error(f"[{request.state.request_id}] - ESLint JSON decode error: {e}")
        logger.error(f"[{request.state.request_id}] - ESLint stdout: {result.stdout}")
        logger.error(f"[{request.state.request_id}] - ESLint stderr: {result.stderr}")
        raise HTTPException(status_code=500, detail="ESLint output parsing failed")
    except IOError as e:
        logger.error(f"[{request.state.request_id}] - File write error: {e}")
        raise HTTPException(status_code=500, detail="Failed to write detection file")
    except Exception as e:
        logger.error(f"[{request.state.request_id}] - ESLint error: {e}")
        raise HTTPException(status_code=500, detail="ESLint check failed")


__all__ = ["router"]
