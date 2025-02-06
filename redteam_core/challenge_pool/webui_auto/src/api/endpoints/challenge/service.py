# -*- coding: utf-8 -*-

import time
import pathlib
from typing import List, Union

import docker
from pydantic import validate_call
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

try:
    from modules.rt_wc_score import MetricsProcessor  # type: ignore
except ImportError:
    from rt_wc_score import MetricsProcessor  # type: ignore

from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.config import config
from api.core.exceptions import BaseHTTPException
from api.endpoints.challenge.schemas import KeyPairPM, MinerInput, MinerOutput
from api.endpoints.challenge import utils as ch_utils
from api.logger import logger


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_bot_dir = _src_dir / "bot"


_KEY_PAIRS: List[KeyPairPM] = ch_utils.gen_key_pairs(
    n_challenge=config.challenge.n_ch_per_epoch,
    key_size=config.api.security.asymmetric.key_size,
)
_CUR_KEY_PAIR: Union[KeyPairPM, None] = None

_CUR_SCORE: Union[float, None] = None


def get_task() -> MinerInput:
    _miner_input = MinerInput(web_url=config.challenge.web_url)
    return _miner_input


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:

    global _KEY_PAIRS
    global _CUR_KEY_PAIR

    if not _KEY_PAIRS:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more web pages available for this epoch!",
        )

    # _CUR_KEY_PAIR = _KEY_PAIRS[-1]
    _CUR_KEY_PAIR = _KEY_PAIRS.pop()

    _nonce = _CUR_KEY_PAIR.nonce
    _public_key = utils.gen_random_string(length=32)

    _templates = Jinja2Templates(directory=(_src_dir / "./templates/html"))
    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"nonce": _nonce, "public_key": _public_key},
    )
    return _html_response


@validate_call
def get_nonce(nonce: str) -> str:

    global _CUR_KEY_PAIR

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more public keys available for this epoch!",
        )

    if _CUR_KEY_PAIR.nonce != nonce:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message=f"Invalid nonce value!",
        )

    if not _CUR_KEY_PAIR.public_key:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"Nonce is already retrieved!",
        )

    _nonce_key: str = _CUR_KEY_PAIR.public_key
    _CUR_KEY_PAIR.public_key = None
    _CUR_KEY_PAIR.nonce = None

    return _nonce_key


@validate_call
def score(miner_output: MinerOutput) -> float:

    global _CUR_SCORE

    _score = 0.0

    logger.debug("Scoring the miner output...")
    try:
        if miner_output.pip_requirements:
            ch_utils.check_pip_requirements(
                pip_requirements=miner_output.pip_requirements,
                target_dt=config.challenge.allowed_pip_pkg_dt,
            )

        ch_utils.copy_bot_files(miner_output=miner_output, src_dir=str(_src_dir))

        _docker_client = docker.from_env()
        _image_name = "bot:latest"
        _container_name = "bot_container"
        ch_utils.build_bot_image(
            docker_client=_docker_client,
            build_dir=str(_bot_dir),
            system_deps=miner_output.system_deps,
            image_name=_image_name,
        )
        ch_utils.run_bot_container(
            docker_client=_docker_client,
            image_name=_image_name,
            container_name=_container_name,
            ulimit=config.challenge.docker_ulimit,
        )

        while True:
            if _CUR_SCORE is not None:
                _score = _CUR_SCORE
                _CUR_SCORE = None
                break

            logger.debug("Waiting for the bot to finish...")
            time.sleep(1)

        logger.debug("Successfully scored the miner output.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


@validate_call
def eval_bot(data: str) -> None:

    global _CUR_KEY_PAIR
    global _CUR_SCORE

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more scoring available for this epoch!",
        )

    _private_key: str = _CUR_KEY_PAIR.private_key
    _CUR_KEY_PAIR = None

    logger.debug("Evaluating the bot...")
    try:
        _plaintext = ch_utils.decrypt(ciphertext=data, private_key=_private_key)

        _metrics_processor = MetricsProcessor()
        _result = _metrics_processor(raw_data=_plaintext)
        _CUR_SCORE = _result["analysis"]["score"]

        logger.debug("Successfully evaluated the bot.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to evaluate the bot: {str(err)}!")
        raise

    return


__all__ = [
    "get_task",
    "get_web",
    "get_nonce",
    "score",
    "eval_bot",
]
