# -*- coding: utf-8 -*-

from pydantic import constr
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

from api.core.constants import ALPHANUM_REGEX
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


@router.get(
    "/web",
    summary="Serves the webpage",
    description="This endpoint serves the webpage for the challenge.",
    response_class=HTMLResponse,
    responses={429: {}},
)
def get_web(request: Request):

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


@router.get(
    "/public_key",
    summary="Get public key",
    description="This endpoint returns the public key.",
    responses={400: {}, 429: {}},
)
def get_public_key(
    request: Request,
    nonce: constr(strip_whitespace=True) = Query(  # type: ignore
        ...,
        min_length=4,
        max_length=64,
        pattern=ALPHANUM_REGEX,
        title="Nonce",
        description="Nonce to prevent replay attacks.",
    ),
):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting public key...")

    _public_key: str
    try:
        _public_key = service.get_public_key(nonce=nonce)

        logger.success(f"[{_request_id}] - Successfully got the public key.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to get the public key!",
        )
        raise

    _response = {"public_key": _public_key}
    return _response


@router.post(
    "/score",
    summary="Evaluate the challenge",
    description="This endpoint evaluates the challenge.",
    response_class=JSONResponse,
    responses={422: {}, 429: {}},
)
async def post_score(
    request: Request, miner_input: MinerInput, miner_output: MinerOutput
):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Evaluating the miner output...")

    _score: float = 0.0
    try:
        _score = await service.async_score(miner_output=miner_output)

        logger.success(f"[{_request_id}] - Successfully evaluated the miner output.")
    except Exception as err:
        if isinstance(err, HTTPException):
            raise

        logger.error(
            f"[{_request_id}] - Failed to evaluate the miner output!",
        )

    return _score


__all__ = ["router"]
