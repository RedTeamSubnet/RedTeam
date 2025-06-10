# -*- coding: utf-8 -*-

from typing import Union

from fastapi import HTTPException, Request

from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.core.responses import BaseResponse


## For HTTPException error:
async def http_exception_handler(request: Request, exc: HTTPException) -> BaseResponse:
    """HTTPException handler.

    Args:
        request (Request      , required): Request object from FastAPI.
        exc     (HTTPException, required): HTTPException object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    _message: str
    _error: Union[dict, str, None] = None

    _http_status, _ = utils.get_http_status(status_code=exc.status_code)
    if isinstance(exc.detail, dict):
        _message = str(exc.detail.get("message", _http_status.phrase))

        _error = exc.detail.get("error")
        if _error:
            if isinstance(_error, dict):
                if ("description" not in _error) and _http_status.description:
                    _error["description"] = _http_status.description
            else:
                _error = str(_error)
    else:
        _message = str(exc.detail)

        _error_code_enum = ErrorCodeEnum.get_by_status_code(status_code=exc.status_code)
        if _error_code_enum:
            _error = _error_code_enum.value.model_dump()

    return BaseResponse(
        request=request,
        status_code=exc.status_code,
        message=_message,
        error=_error,
        headers=exc.headers,
    )


__all__ = ["http_exception_handler"]
