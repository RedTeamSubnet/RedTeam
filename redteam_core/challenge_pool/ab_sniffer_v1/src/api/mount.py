# -*- coding: utf-8 -*-

import pathlib

from pydantic import validate_call
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


@validate_call(config={"arbitrary_types_allowed": True})
def add_mounts(app: FastAPI) -> None:
    """Add mounts to FastAPI app.

    Args:
        app (FastAPI): FastAPI app instance.
    """

    _src_dir = pathlib.Path(__file__).parent.parent.resolve()

    app.mount(
        path="/static",
        app=StaticFiles(directory=str(_src_dir / "./templates/static")),
        name="static",
    )
    return


__all__ = ["add_mounts"]
