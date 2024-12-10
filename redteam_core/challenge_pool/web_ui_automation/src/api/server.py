# -*- coding: utf-8 -*-

## Third-party libraries
import uvicorn
from pydantic import validate_call
from fastapi import FastAPI

## Internal modules
from .config import config
from .lifespan import lifespan
from .middleware import add_middlewares
from .router import add_routers
from .exception import add_exception_handlers


app = FastAPI(
    title=config.api.name,
    version=config.version,
    lifespan=lifespan,
    **config.api.docs.model_dump(exclude={"enabled"}),
)

add_middlewares(app=app)
add_routers(app=app)
add_exception_handlers(app=app)


@validate_call
def run_server(app: str = "main:app") -> None:
    """Run uvicorn server.

    Args:
        app (str, optional): Application instance. Defaults to "main:app".
    """

    uvicorn.run(
        app=app,
        host=config.api.bind_host,
        port=config.api.port,
        access_log=False,
        server_header=False,
        proxy_headers=config.api.behind_proxy,
        forwarded_allow_ips=config.api.security.forwarded_allow_ips,
        **config.api.dev.model_dump(),
    )


__all__ = ["app", "run_server"]
