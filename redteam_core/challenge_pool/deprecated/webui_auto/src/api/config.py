# -*- coding: utf-8 -*-

from onion_config import ConfigLoader
from beans_logging import logger

from .configs import MainConfig


config: MainConfig
try:
    _config_loader = ConfigLoader(config_schema=MainConfig)
    # Main config object:
    config: MainConfig = _config_loader.load()
except Exception:
    logger.exception("Failed to load config:")
    raise SystemExit(1)


__all__ = ["config"]
