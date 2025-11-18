# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse

from api.endpoints.challenge.schemas import MinerInput, MinerOutput
from api.endpoints.challenge import service
from api.logger import logger
from pydantic import BaseModel


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
    "/driver",
    description="This endpoint posts the driver name for scoring.",
    responses={422: {}},
)
def post_driver(
    request: Request,
    driver: str = Body(..., embed=False),
):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Posting driver name for scoring ...")
    try:
        service.post_driver(driver, _request_id)
        logger.success(
            f"[{_request_id}] - Successfully posted driver name for scoring."
        )
    except Exception as err:
        logger.error(
            f"[{_request_id}] - Error posting driver name for scoring: {str(err)}"
        )
        raise HTTPException(
            status_code=500, detail="Error in posting driver name for scoring"
        )

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


class ESLintRequest(BaseModel):
    js_content: str

    class Config:
        json_schema_extra = {
            "example": {
                "js_content": "// Your JavaScript detection code here\nconsole.log('Hello World');"
            }
        }


__all__ = ["router"]
