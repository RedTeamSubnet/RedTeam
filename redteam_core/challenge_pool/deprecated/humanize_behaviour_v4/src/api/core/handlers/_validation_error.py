# -*- coding: utf-8 -*-

from fastapi import Request
from fastapi.exceptions import RequestValidationError

from api.core.constants import ErrorCodeEnum
from api.core.responses import BaseResponse


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
    _details = exc.errors()
    for _detail in _details:
        if ("ctx" in _detail) and ("error" in _detail["ctx"]):
            _detail["ctx"]["error"] = str(_detail["ctx"]["error"])

    _error["detail"] = _details

    return BaseResponse(
        request=request, status_code=422, message=_message, error=_error
    )


__all__ = ["validation_error_handler"]
