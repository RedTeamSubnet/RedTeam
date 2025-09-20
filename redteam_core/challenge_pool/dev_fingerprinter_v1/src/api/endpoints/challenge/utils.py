# -*- coding: utf-8 -*-

import os
import json
import pathlib
import subprocess
from json import JSONDecodeError
from subprocess import CalledProcessError

from pydantic import validate_call

from api.core import utils
from api.logger import logger


_APP_DIR = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_ESLINT_CONFIG_PATH = os.path.join(_APP_DIR, "eslint.config.mjs")


@validate_call
def save_fp_js(request_id: str, content: str, file_path: str) -> None:
    """Save the fingerprinter.js content to a specified file path.

    Args:
        content   (str, required): The content of the fingerprinter.js file.
        file_path (str, required): The path where the fingerprinter.js file will be saved.

    Raises:
        Exception: If there is an error while saving the file.
    """

    file_path = file_path.strip()
    if not file_path:
        raise ValueError("`file_path` argument value is empty!")

    logger.info(f"[{request_id}] - Saving '{file_path}' fingerprinter.js file...")
    try:
        _parent_dir = os.path.dirname(file_path)
        utils.create_dir(_parent_dir)
        utils.remove_file(file_path)

        with open(file_path, "w") as _file:
            _file.write(content)

        logger.info(
            f"[{request_id}] - Successfully saved '{file_path}' fingerprinter.js file."
        )
    except Exception:
        logger.error(
            f"[{request_id}] - Failed to save '{file_path}' fingerprinter.js file!"
        )
        raise

    return


@validate_call
def run_eslint(
    request_id: str,
    file_path: str,
    config_path: str = _ESLINT_CONFIG_PATH,
    prefix_dir: str = _APP_DIR,
    timeout: int = 30,
) -> tuple[bool, dict]:

    _is_passed = False
    _report = {}

    logger.info(f"[{request_id}] - Running ESLint to check '{file_path}' file...")
    _report_stdout = ""
    try:
        _parent_dir = os.path.dirname(file_path)
        # fmt: off
        _cmd = ["npx", "--prefix", prefix_dir, "eslint", "-c", config_path, "-f", "json", file_path]
        # fmt: on
        _result = subprocess.run(
            _cmd,
            cwd=_parent_dir,
            capture_output=True,
            check=True,
            text=True,
            timeout=timeout,
        )

        if _result.stdout:
            _report_stdout = _result.stdout

        _is_passed = True
        logger.success(
            f"[{request_id}] - Successfully ran ESLint on '{file_path}' file."
        )
    except CalledProcessError as err:
        if err.stderr:
            logger.error(
                f"[{request_id}] - Failed to run ESLint on '{file_path}' file!"
            )
            raise

        if err.stdout:
            _report_stdout = err.stdout

    except FileNotFoundError:
        logger.error(f"[{request_id}] - Not found 'npx' command on this system!")
        raise
    except Exception:
        logger.error(
            f"[{request_id}] - Unexpected error occurred while running ESLint on '{file_path}' file!"
        )
        raise

    if _report_stdout:
        try:
            _report = json.loads(_report_stdout)[0]
        except JSONDecodeError:
            logger.error(
                f"[{request_id}] - Failed to parse ESLint output as JSON for '{file_path}' file!"
            )
            raise

    _report.pop("source", None)
    _report.pop("filePath", None)

    if not _is_passed:
        logger.warning(
            f"[{request_id}] - ESLint found issues in '{file_path}' file: {_report}!"
        )

    return _is_passed, _report


__all__ = [
    "save_fp_js",
    "run_eslint",
]
