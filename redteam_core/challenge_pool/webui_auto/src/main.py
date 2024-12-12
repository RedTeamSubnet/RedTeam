#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Internal modules
from api.server import app, run_server
from api.logger import logger


if __name__ == "__main__":
    logger.info(f"Starting server from 'main.py'...")
    run_server()


__all__ = ["app"]
