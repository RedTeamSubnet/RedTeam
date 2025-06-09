# -*- coding: utf-8 -*-

import pathlib

from onion_config import ConfigLoader
from beans_logging import logger

from api.core.configs import MainConfig


config: MainConfig
try:
    _parent_dir = pathlib.Path(__file__).parent.resolve()
    _config_loader = ConfigLoader(
        config_schema=MainConfig, configs_dirs=[str(_parent_dir / "configs")]
    )
    # Main config object:
    config: MainConfig = _config_loader.load()
except Exception:
    logger.exception("Failed to load config:")
    raise SystemExit(1)


__all__ = ["config"]
