# -*- coding: utf-8 -*-

from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse

from api.endpoints.challenge.schemas import MinerInput, MinerOutput
from api.endpoints.challenge import service
from api.logger import logger


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

    return {"similarity_score": _score}


__all__ = ["router"]
