#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Standard libraries
import os
import sys
import json
import logging
import subprocess

## Internal modules
from driver import WebUIAutomate


logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S %z",
        format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
    )

    logger.info("Starting WebUI automation bot...")

    _web_url = os.getenv("WUC_WEB_URL")
    if not _web_url:
        _command = "ip route | awk '/default/ { print $3 }'"
        _host = subprocess.check_output(_command, shell=True, text=True).strip()
        _web_url = f"https://{_host}:10001/web"

    _action_list = os.getenv("WUC_ACTION_LIST")
    if not _action_list:
        raise ValueError("WUC_ACTION_LIST is not set!")

    _action_list = json.loads(_action_list)
    if not isinstance(_action_list, list):
        raise ValueError("WUC_ACTION_LIST must be a list!")

    _webui_automate = WebUIAutomate(web_url=_web_url, config={"actions": _action_list})
    _webui_automate()

    logger.info("Done!\n")
    return


if __name__ == "__main__":
    main()
