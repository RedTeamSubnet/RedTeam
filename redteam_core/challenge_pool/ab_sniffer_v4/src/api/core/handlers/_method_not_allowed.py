# -*- coding: utf-8 -*-

from fastapi import HTTPException, Request

from api.core.constants import ErrorCodeEnum
from api.core.responses import BaseResponse


## For 405 status code:
async def method_not_allowed_handler(
    request: Request, exc: HTTPException
) -> BaseResponse:
    """405 status code handler.

    Args:
        request (Request      , required): Request object from FastAPI.
        exc     (HTTPException, required): HTTPException object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    _error = ErrorCodeEnum.METHOD_NOT_ALLOWED.value.model_dump()
    _message: str = _error.get("message")

    return BaseResponse(
        request=request, status_code=405, message=_message, error=_error
    )


__all__ = ["method_not_allowed_handler"]
