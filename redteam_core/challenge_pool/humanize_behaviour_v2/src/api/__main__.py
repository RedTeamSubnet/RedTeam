# -*- coding: utf-8 -*-

## Third-party libraries
from fastapi import FastAPI

## Internal modules
from api.bootstrap import create_app, run_server
from api.logger import logger


app: FastAPI = create_app()


def main() -> None:
    """Main function."""

    run_server(app="api.__main__:app")
    return


if __name__ == "__main__":
    logger.info(f"Starting server from '__main__.py'...")
    main()

__all__ = ["app"]
