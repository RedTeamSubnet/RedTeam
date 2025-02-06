# -*- coding: utf-8 -*-

import base64
import pathlib
from typing import List, Union

import docker
from pydantic import validate_call
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

try:
    from modules.rt_wc_score import MetricsProcessor  # type: ignore
except ImportError:
    from rt_wc_score import MetricsProcessor  # type: ignore

import vault_unlock
from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.config import config
from api.core.exceptions import BaseHTTPException
from api.helpers.crypto import asymmetric as asymmetric_helper
from api.helpers.crypto import symmetric as symmetric_helper
from api.endpoints.challenge.schemas import KeyPairPM, MinerInput, MinerOutput
from api.endpoints.challenge import utils as ch_utils
from api.logger import logger

_cur_dir = pathlib.Path(__file__).parent.resolve()
_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_bot_dir = _src_dir / "bot"


_KEY_PAIRS: List[KeyPairPM] = ch_utils.gen_key_pairs(
    n_challenge=config.challenge.n_ch_per_epoch,
    key_size=config.api.security.asymmetric.key_size,
)
_CUR_KEY_PAIR: Union[KeyPairPM, None] = None


@validate_call
def _decrypt(ciphertext: str) -> str:

    global _CUR_KEY_PAIR

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more scoring available for this epoch!",
        )

    _private_key: str = _CUR_KEY_PAIR.private_key
    _CUR_KEY_PAIR = None

    # _ciphertext, _key, _iv = _extract(ciphertext=ciphertext)
    # _ciphertext, _key, _iv = ("", "", "")

    # _private_key: PrivateKeyTypes = serialization.load_pem_private_key(
    #     data=_private_key.encode()
    # )
    # _key_bytes: bytes = asymmetric_helper.decrypt_with_private_key(
    #     ciphertext=_key,
    #     private_key=_private_key,
    #     base64_decode=True,
    # )

    # _iv_bytes: bytes = base64.b64decode(_iv)
    # _plaintext: str = symmetric_helper.decrypt_aes_cbc(
    #     ciphertext=_ciphertext,
    #     key=_key_bytes,
    #     iv=_iv_bytes,
    #     base64_decode=True,
    #     as_str=True,
    # )
    # cur dir

    _plaintext: str = vault_unlock.decrypt_payload(
        encrypted_text=ciphertext, private_key_pem=_private_key
    )

    return _plaintext


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

        logger.debug("Successfully scored the miner output.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


@validate_call
def eval_bot(data: str) -> float:

    _score = 0.0

    logger.debug("Evaluating the bot...")
    logger.debug(f"Data: {data}")

    try:
        _plaintext = _decrypt(ciphertext=data)
        _metrics_processor = MetricsProcessor()
        _score = _metrics_processor(raw_data=_plaintext)

        logger.debug("Successfully evaluated the bot.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to evaluate the bot: {str(err)}!")
        raise

    return _score


__all__ = [
    "get_task",
    "get_web",
    "get_nonce",
    "score",
    "eval_bot",
]
