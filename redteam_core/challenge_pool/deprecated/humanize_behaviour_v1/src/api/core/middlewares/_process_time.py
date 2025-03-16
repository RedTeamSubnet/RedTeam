# -*- coding: utf-8 -*-

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Calculate process time of each request and add it to response 'X-Process-Time' header.

    Inherits:
        BaseHTTPMiddleware: Base HTTP middleware from Starlette.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        _start_time: int = time.perf_counter_ns()
        response: Response = await call_next(request)
        _end_time: int = time.perf_counter_ns()
        _response_time: float = round((_end_time - _start_time) / 1_000_000, 1)
        response.headers["X-Process-Time"] = str(_response_time)

        return response


__all__ = ["ProcessTimeMiddleware"]
