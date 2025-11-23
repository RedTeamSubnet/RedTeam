from fastapi import APIRouter, Request, HTTPException, Body, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from api.core.dependencies.auth import auth_api_key
from api.endpoints.challenge.schemas import (
    MinerInput,
    MinerOutput,
    SubmissionPayloadsPM,
)
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
    responses={400: {}, 422: {}, 401: {}},
    dependencies=[Depends(auth_api_key)],
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
            raise

        logger.error(
            f"[{_request_id}] - Failed to evaluate the miner output!",
        )
        raise

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
    "/_payload",
    description="This endpoint posts the human score.",
    responses={422: {}},
)
def post_payload(request: Request, body: SubmissionPayloadsPM = Body(...)):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Received submission payload.")
    try:
        logger.info(f"{body}")
        service.submit_payload(body)
        logger.success(f"[{_request_id}] - Successfully saved payload.")
    except Exception as err:
        logger.error(f"[{_request_id}] - Error saving payload: {str(err)}")
        raise HTTPException(status_code=500, detail="Error in saving payloadß")

    return


@router.get(
    "/results", response_class=JSONResponse, dependencies=[Depends(auth_api_key)]
)
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


__all__ = ["router"]
