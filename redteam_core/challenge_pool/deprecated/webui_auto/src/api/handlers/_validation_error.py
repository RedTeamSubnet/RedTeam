# -*- coding: utf-8 -*-

from fastapi import Request
from fastapi.exceptions import RequestValidationError

from api.constants import ErrorCodeEnum
from api.responses import BaseResponse


## For RequestValidationError error:
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> BaseResponse:
    """RequestValidationError handler for validation error.

    Args:
        request (Request               , required): Request object from FastAPI.
        exc     (RequestValidationError, required): RequestValidationError object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    _message = "Validation error!"
    _error = ErrorCodeEnum.UNPROCESSABLE_ENTITY.value.model_dump()
    _error["description"] = str(exc)
    _error["detail"] = exc.errors()

    return BaseResponse(
        request=request, status_code=422, message=_message, error=_error
    )


__all__ = ["validation_error_handler"]
