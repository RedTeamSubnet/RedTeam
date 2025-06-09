# -*- coding: utf-8 -*-

from fastapi import HTTPException, Request

from api.core.constants import ErrorCodeEnum
from api.core.responses import BaseResponse


## For 404 status code:
async def not_found_handler(request: Request, exc: HTTPException) -> BaseResponse:
    """404 status code handler.

    Args:
        request (Request      , required): Request object from FastAPI.
        exc     (HTTPException, required): HTTPException object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    _error = ErrorCodeEnum.NOT_FOUND.value.model_dump()
    _message: str = _error.get("message")

    if hasattr(exc, "detail") and isinstance(exc.detail, dict):
        _message = exc.detail.get("message", _message)
        _error = exc.detail.get("error", _error)

    return BaseResponse(
        request=request, status_code=404, message=_message, error=_error
    )


__all__ = ["not_found_handler"]
