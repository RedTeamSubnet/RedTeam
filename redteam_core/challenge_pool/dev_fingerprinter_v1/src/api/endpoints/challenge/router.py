# -*- coding: utf-8 -*-

from fastapi import APIRouter, Request, HTTPException, Body, Depends
from fastapi.responses import JSONResponse

from api.core.constants import ErrorCodeEnum, ALPHANUM_HYPHEN_REGEX
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.core.exceptions import BaseHTTPException
from api.core.dependencies.auth import auth_api_key
from api.logger import logger

from .schemas import MinerInput, MinerOutput
from . import service


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
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            f"[{_request_id}] - Failed to get task!",
        )
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to get task!",
        )

    return _miner_input


@router.post(
    "/score",
    summary="Score",
    description="This endpoint score miner output.",
    response_class=JSONResponse,
    responses={422: {}},
)
def post_score(request: Request, miner_input: MinerInput, miner_output: MinerOutput):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Scoring the miner output...")

    _score: float = 0.0
    try:
        _score = service.score(request_id=_request_id, miner_output=miner_output)
        logger.success(
            f"[{_request_id}] - Successfully scored the miner output: {_score}"
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"[{_request_id}] - Failed to score the miner output!")
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to score the miner output!",
        )

    return _score


@router.post(
    "/compare",
    summary="Compare miner outputs",
    description="This endpoint compares a miner's output to a reference output.",
    responses={422: {}},
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


@router.post(
    "/_fingerprint",
    summary="Set device fingerprint",
    description="This endpoint receives the device fingerprint from the DFP proxy server.",
    response_model=BaseResPM,
    responses={401: {}, 422: {}},
    dependencies=[Depends(auth_api_key)],
)
def post_fingerprint(
    request: Request,
    order_id: int = Body(..., ge=0, lt=1000000, examples=[0]),
    fingerprint: str = Body(
        ..., min_length=2, max_length=128, pattern=ALPHANUM_HYPHEN_REGEX
    ),
):
    _request_id = request.state.request_id
    logger.info(
        f"[{_request_id}] - Setting device fingerprint as {{'order_id': {order_id}, 'fingerprint': '{fingerprint}'}} ..."
    )

    try:
        service.set_fingerprint(
            order_id=order_id,
            fingerprint=fingerprint,
        )

        logger.success(
            f"[{_request_id}] - Successfully set device fingerprint as {{'order_id': {order_id}, 'fingerprint': '{fingerprint}'}}."
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            f"[{_request_id}] - Failed to set device fingerprint as {{'order_id': {order_id}, 'fingerprint': '{fingerprint}'}}!"
        )
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to set device fingerprint!",
        )

    _response = BaseResponse(
        request=request, message="Successfully set device fingerprint."
    )
    return _response


@router.post(
    "/eslint",
    summary="Check ESLint",
    description="This endpoint checks if the provided JavaScript content passes ESLint.",
    response_model=BaseResPM,
    responses={422: {}},
)
def post_eslint(request: Request, miner_output: MinerOutput):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Checking fingerprinter.js with ESLint...")

    _is_passed = False
    _report = {}
    try:
        _is_passed, _report = service.check_eslint(
            request_id=_request_id, fp_js=miner_output.fingerprinter_js
        )

        if not _is_passed:
            raise BaseHTTPException(
                error_enum=ErrorCodeEnum.UNPROCESSABLE_ENTITY,
                message="Fingerprinter.js failed to pass ESLint!",
                detail=_report,
            )

        logger.success(
            f"[{_request_id}] - Successfully checked fingerprinter.js with ESLint."
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            f"[{_request_id}] - Failed to check fingerprinter.js with ESLint!"
        )
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to check fingerprinter.js with ESLint!",
        )

    _response = BaseResponse(
        request=request,
        message="Successfully checked fingerprinter.js with ESLint.",
        content={
            "is_passed": _is_passed,
            "report": _report,
        },
    )
    return _response


__all__ = ["router"]
