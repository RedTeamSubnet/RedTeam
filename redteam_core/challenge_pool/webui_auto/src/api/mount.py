# -*- coding: utf-8 -*-

from pydantic import validate_call
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


@validate_call(config={"arbitrary_types_allowed": True})
def add_mounts(app: FastAPI) -> None:
    """Add mounts to FastAPI app.

    Args:
        app (FastAPI): FastAPI app instance.
    """

    app.mount(
        path="/static", app=StaticFiles(directory="./templates/static"), name="static"
    )


__all__ = ["add_mounts"]
