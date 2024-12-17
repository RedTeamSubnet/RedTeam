# -*- coding: utf-8 -*-

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import config
from .helpers.crypto import asymmetric as asymmetric_helper
from .helpers.crypto import ssl as ssl_helper
from .logger import logger


def pre_check() -> None:
    """Pre-check function before creating and starting FastAPI application."""

    if config.api.security.ssl.enabled:
        ssl_helper.generate_ssl_certs(
            ssl_dir=config.api.paths.ssl_dir,
            cert_fname=config.api.security.ssl.cert_fname,
            key_fname=config.api.security.ssl.key_fname,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.
    Startup and shutdown events are logged.

    Args:
        app (FastAPI, required): FastAPI application instance.
    """

    logger.info("Preparing to startup...")
    if config.api.security.asymmetric.generate:
        await asymmetric_helper.async_create_keys(
            asymmetric_keys_dir=config.api.paths.asymmetric_keys_dir,
            key_size=config.api.security.asymmetric.key_size,
            private_key_fname=config.api.security.asymmetric.private_key_fname,
            public_key_fname=config.api.security.asymmetric.public_key_fname,
        )

    # Add startup code here...
    logger.success("Finished preparation to startup.")

    logger.opt(colors=True).info(f"Version: <c>{config.version}</c>")
    logger.opt(colors=True).info(f"API version: <c>{config.api.version}</c>")
    logger.opt(colors=True).info(f"API prefix: <c>{config.api.prefix}</c>")

    _protocol = "http"
    if config.api.security.ssl.enabled:
        _protocol = "https"

    logger.opt(colors=True).info(
        f"Listening on: <c>{_protocol}://{config.api.bind_host}:{config.api.port}</c>"
    )

    yield

    logger.info("Praparing to shutdown...")
    # Add shutdown code here...
    logger.success("Finished preparation to shutdown.")


__all__ = ["pre_check", "lifespan"]
