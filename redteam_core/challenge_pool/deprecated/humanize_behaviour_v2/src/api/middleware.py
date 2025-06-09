# -*- coding: utf-8 -*-

from pydantic import validate_call
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from beans_logging_fastapi import (
    HttpAccessLogMiddleware,
    RequestHTTPInfoMiddleware,
    ResponseHTTPInfoMiddleware,
)

from api.config import config
from api.core.middlewares import ProcessTimeMiddleware, RequestIdMiddleware


@validate_call(config={"arbitrary_types_allowed": True})
def add_middlewares(app: FastAPI) -> None:
    """Add middlewares to FastAPI app.

    Args:
        app (FastAPI): FastAPI app instance.
    """

    ## Add more middlewares here...
    app.add_middleware(ResponseHTTPInfoMiddleware)
    app.add_middleware(
        HttpAccessLogMiddleware,
        debug_format=config.logger.extra.http_std_debug_format,
        msg_format=config.logger.extra.http_std_msg_format,
    )
    app.add_middleware(
        RequestHTTPInfoMiddleware,
        has_proxy_headers=config.api.behind_proxy,
        has_cf_headers=config.api.behind_cf_proxy,
    )
    app.add_middleware(GZipMiddleware, minimum_size=config.api.gzip_min_size)
    app.add_middleware(CORSMiddleware, **config.api.security.cors.model_dump())
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=config.api.security.allowed_hosts
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ProcessTimeMiddleware)

    return


__all__ = ["add_middlewares"]
