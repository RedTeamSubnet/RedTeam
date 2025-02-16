# -*- coding: utf-8 -*-

from pydantic import constr
from fastapi import APIRouter, Request, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse

from api.core.constants import ALPHANUM_REGEX, ALPHANUM_CUSTOM_REGEX
from api.core.responses import BaseResponse
from api.endpoints.challenge.schemas import MinerInput, MinerOutput
from api.endpoints.challenge import service
from api.logger import logger


router = APIRouter(tags=["Challenge"])


@router.get(
    "/task",
    summary="Get task",
    description="This endpoint returns the webpage URL for the challenge.",
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
    reset: bool = Query(
        default=False,
        title="Reset",
        description="Reset the challenge.",
        examples=[False],
    ),
):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Evaluating the miner output...")

    _score: float = 0.0
    try:
        _score = service.score(miner_output=miner_output, reset=reset)

        logger.success(f"[{_request_id}] - Successfully evaluated the miner output.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to evaluate the miner output!",
        )
        raise

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
    "/_random_val",
    summary="Random value",
    responses={401: {}, 422: {}, 429: {}},
)
def _post_random_val(
    request: Request,
    random_val: constr(strip_whitespace=True) = Body(  # type: ignore
        ...,
        embed=True,
        min_length=4,
        max_length=64,
        pattern=ALPHANUM_REGEX,
        title="Random value",
        description="Random value.",
        examples=["a1b2c3d4e5f6g7h8"],
    ),
):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Checking random val...")

    _nonce_val: str
    try:
        _nonce_val = service.get_random_val(nonce=random_val)

        logger.success(f"[{_request_id}] - Successfully checked the random val.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to check the random val!",
        )
        raise

    _response = {"nonce_val": _nonce_val}
    return _response


@router.post(
    "/_eval",
    summary="Evaluate",
    description="This endpoint evaluate.",
    responses={422: {}, 429: {}},
)
def _post_eval_bot(
    request: Request,
    data: str = Body(
        ...,
        embed=True,
        min_length=2,
        pattern=ALPHANUM_CUSTOM_REGEX,
        title="Data",
        description="Bot data to evaluate.",
        examples=["data"],
    ),
):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Evaluating the bot...")

    try:
        service.eval_bot(data=data)

        logger.success(f"[{_request_id}] - Successfully evaluated the bot.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to evaluate the bot!",
        )
        raise

    _response = BaseResponse(request=request, message="Successfully evaluated the bot.")
    return _response


__all__ = ["router"]
