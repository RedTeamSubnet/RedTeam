# -*- coding: utf-8 -*-

from functools import lru_cache

from beans_logging import logger

from bot import WebUIAutomate


@lru_cache()
def get_webui_automate() -> WebUIAutomate:

    _webui_automate = None
    try:
        _webui_automate = WebUIAutomate(username="username", password="password")
    except Exception:
        logger.exception(f"Failed to load WebUIAutomate!")
        exit(2)
    return _webui_automate


__all__ = ["get_webui_automate"]