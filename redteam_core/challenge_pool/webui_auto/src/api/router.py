# -*- coding: utf-8 -*-

from pydantic import validate_call
from fastapi import FastAPI, APIRouter

from .config import config
from .routers.utils import router as utils_router
from .routers.challenge import router as challenge_router


@validate_call(config={"arbitrary_types_allowed": True})
def add_routers(app: FastAPI) -> None:
    """Add routers to FastAPI app.

    Args:
        app (FastAPI): FastAPI app instance.
    """

    _api_router = APIRouter(prefix=config.api.prefix)
    _api_router.include_router(utils_router)
    _api_router.include_router(challenge_router)
    # Add more API routers here...

    app.include_router(_api_router)


__all__ = ["add_routers"]
