# -*- coding: utf-8 -*-

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from api.core.constants import ErrorCodeEnum
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.core.exceptions import BaseHTTPException
from api.core.services import utils as utils_services
from api.logger import logger


router = APIRouter(tags=["Utils"])


@router.get(
    "/",
    summary="Base",
    description="Base path for all API endpoints.",
    response_model=BaseResPM,
)
async def get_base(request: Request):
    return BaseResponse(request=request, message="Welcome to the REST API service!")


@router.get(
    "/ping",
    summary="Ping",
    description="Check if the service is up and running.",
    response_model=BaseResPM,
)
async def get_ping(request: Request):
    return BaseResponse(
        request=request, message="Pong!", headers={"Cache-Control": "no-cache"}
    )


@router.get(
    "/health",
    summary="Health",
    description="Check health of all related services.",
    response_class=JSONResponse,
    responses={503: {}},
)
def get_health(request: Request, response: Response):

    _request_id = request.state.request_id
    _response_json = {}
    try:
        _response_json = utils_services.check_health(request_id=_request_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            f"[{_request_id}] - Failed to check health of DFP proxy server and devices!"
        )
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to check health!",
        )

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return _response_json


__all__ = ["router"]
