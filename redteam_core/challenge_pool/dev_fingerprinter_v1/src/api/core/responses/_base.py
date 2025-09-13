# -*- coding: utf-8 -*-

from http import HTTPStatus
from typing import Any, Optional, Dict, Type

from pydantic import validate_call, conint, constr
from starlette.background import BackgroundTask
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.config import config
from api.core import utils
from api.core.schemas import BaseResPM


class BaseResponse(JSONResponse):
    """Base response class for most of the API responses with JSON format.
    Based on BaseResPM schema.

    Inherits:
        JSONResponse: JSON response class from FastAPI.
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        content: Any = None,
        status_code: Optional[conint(ge=100, le=599)] = 200,  # type: ignore
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[constr(strip_whitespace=True)] = None,  # type: ignore
        background: Optional[BackgroundTask] = None,
        request: Optional[Request] = None,
        message: Optional[
            constr(strip_whitespace=True, min_length=1, max_length=256)  # type: ignore
        ] = None,
        links: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
        error: Any = None,
        response_schema: Optional[Type[BaseResPM]] = BaseResPM,
    ) -> None:
        """Constructor method for BaseResponse class.
        This will prepare the most response data and pass it to `JSONResponse` parent class constructor.

        Args:
            content         (Any                      , optional): Main data content for response. Defaults to None.
            status_code     (Optional[int]            , optional): HTTP status code: [100 <= status_code <= 599]. Defaults to 200.
            headers         (Optional[Dict[str, str]] , optional): HTTP headers. Defaults to None.
            media_type      (Optional[str]            , optional): Media type for 'Content-Type' header. Defaults to None.
            background      (Optional[BackgroundTask] , optional): Background task. Defaults to None.
            request         (Optional[Request]        , optional): Request object from FastAPI. Defaults to None.
            message         (Optional[str]            , optional): Message for response: [1 <= len(message) <= 256]. Defaults to None.
            links           (Optional[Dict[str, Any]] , optional): Links for response. Defaults to None.
            meta            (Optional[Dict[str, Any]] , optional): Meta data for response. Defaults to None.
            error           (Any                      , optional): Error data for response. Defaults to None.
            response_schema (Optional[Type[BaseResPM]], optional): Response schema type. Defaults to `Type[BaseResPM]`.
        """

        _http_status: HTTPStatus
        _http_status, _ = utils.get_http_status(status_code=status_code)

        if not message:
            if error and isinstance(error, dict) and ("message" in error):
                message = str(error["message"])
            else:
                message: str = _http_status.phrase

        if not links:
            links = {}

        if not meta:
            meta = {}

        if not headers:
            headers = {}

        if request:
            _request_id: str = request.state.request_id

            links["self"] = f"{utils.get_relative_url(request)}"
            meta["request_id"] = _request_id
            meta["method"] = request.method
            meta["base_url"] = str(request.base_url)[:-1]

            if "X-Request-Id" not in headers:
                headers["X-Request-Id"] = _request_id

        meta["api_version"] = config.api.version
        meta["version"] = config.version

        if error and isinstance(error, dict):
            if ("code" in error) and ("X-Error-Code" not in headers):
                headers["X-Error-Code"] = error.get("code")

            if (not config.debug) and (500 <= status_code) and ("detail" in error):
                error["detail"] = None

        if (not error) and (400 <= status_code) and _http_status.description:
            error = f"{_http_status.description}!"

        if (400 <= status_code) and ("X-Error-Code" not in headers):
            headers["X-Error-Code"] = f"{status_code}_00000"

        if 500 <= status_code:
            if "Cache-Control" not in headers:
                headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

            if "Pragma" not in headers:
                headers["Pragma"] = "no-cache"

            if "Expires" not in headers:
                headers["Expires"] = "0"

            if (status_code == 503) and ("Retry-After" not in headers):
                headers["Retry-After"] = "1800"

        _response_pm = response_schema(
            message=message, data=content, links=links, meta=meta, error=error
        )
        _content = jsonable_encoder(obj=_response_pm, by_alias=True)

        super().__init__(
            content=_content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
        return


__all__ = ["BaseResponse"]
