# -*- coding: utf-8 -*-

from uuid import uuid4
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Get 'X-Request-ID' or 'X-Correlation-ID' from request header or generate a new one.
    Then add it to `request.state.request_id` and response 'X-Request-ID' header.

    Inherits:
        BaseHTTPMiddleware: Base HTTP middleware from Starlette.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        _request_id: str = uuid4().hex
        if "X-Request-ID" in request.headers:
            _request_id: str = request.headers.get("X-Request-ID")
        elif "X-Correlation-ID" in request.headers:
            _request_id: str = request.headers.get("X-Correlation-ID")

        request.state.request_id = _request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = _request_id

        return response


__all__ = ["RequestIdMiddleware"]
