# -*- coding: utf-8 -*-

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import config
from .helpers.crypto import asymmetric_keys as asymmetric_keys_helper
from .logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.
    Startup and shutdown events are logged.

    Args:
        app (FastAPI, required): FastAPI application instance.
    """

    logger.info("Preparing to startup...")
    if config.api.security.asymmetric_keys.auto_generate:
        await asymmetric_keys_helper.async_create_keys(
            asymmetric_keys_dir=config.api.paths.asymmetric_keys_dir,
            key_size=config.api.security.asymmetric_keys.key_size,
            private_key_fname=config.api.security.asymmetric_keys.private_key_fname,
            public_key_fname=config.api.security.asymmetric_keys.public_key_fname,
        )
    # Add startup code here...
    logger.success("Finished preparation to startup.")
    logger.opt(colors=True).info(f"Version: <c>{config.version}</c>")
    logger.opt(colors=True).info(f"API version: <c>{config.api.version}</c>")
    logger.opt(colors=True).info(f"API prefix: <c>{config.api.prefix}</c>")
    logger.opt(colors=True).info(
        f"Listening on: <c>http://{config.api.bind_host}:{config.api.port}</c>"
    )

    yield

    logger.info("Praparing to shutdown...")
    # Add shutdown code here...
    logger.success("Finished preparation to shutdown.")


__all__ = ["lifespan"]
