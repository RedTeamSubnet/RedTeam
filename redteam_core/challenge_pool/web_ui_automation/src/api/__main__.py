# -*- coding: utf-8 -*-

## Internal modules
from .server import run_server
from .logger import logger


if __name__ == "__main__":
    logger.info(f"Starting server from '__main__.py'...")
    run_server(app="api:app")
