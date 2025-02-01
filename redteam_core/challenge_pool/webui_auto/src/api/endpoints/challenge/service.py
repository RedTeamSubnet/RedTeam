# -*- coding: utf-8 -*-

import base64
import pathlib
from typing import List, Tuple, Union, Dict

import aiofiles
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

from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.config import config
from api.core.exceptions import BaseHTTPException
from api.helpers.crypto import asymmetric as asymmetric_helper
from api.helpers.crypto import symmetric as symmetric_helper
from api.endpoints.challenge.schemas import KeyPairPM, MinerInput, MinerOutput
from api.logger import logger


@validate_call
def _gen_key_pairs(n_challenge: int) -> List[KeyPairPM]:

    _key_pairs: List[KeyPairPM] = []
    for _ in range(n_challenge):
        _key_pair: Tuple[str, str] = asymmetric_helper.gen_key_pair(
            key_size=config.api.security.asymmetric.key_size, as_str=True
        )
        _private_key, _public_key = _key_pair
        _nonce = utils.gen_random_string(length=32)
        _key_pair_pm = KeyPairPM(
            private_key=_private_key, public_key=_public_key, nonce=_nonce
        )
        _key_pairs.append(_key_pair_pm)

    return _key_pairs


_KEY_PAIRS: List[KeyPairPM] = _gen_key_pairs(
    n_challenge=config.api.security.n_challenges_per_epoch
)
_CUR_KEY_PAIR: Union[KeyPairPM, None] = None


def get_task() -> MinerInput:
    _miner_input = MinerInput(web_url=config.web.url)
    return _miner_input


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:

    global _CUR_KEY_PAIR

    if not _KEY_PAIRS:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more web pages available for this epoch!",
        )

    _CUR_KEY_PAIR = _KEY_PAIRS[-1]

    _nonce = _CUR_KEY_PAIR.nonce
    _CUR_KEY_PAIR.nonce = None
    _public_key = utils.gen_random_string(length=32)

    _src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
    _templates = Jinja2Templates(directory=(_src_dir / "./templates/html"))
    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"nonce": _nonce, "public_key": _public_key},
    )
    return _html_response


@validate_call
def get_public_key(nonce: str) -> str:

    global _CUR_KEY_PAIR

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more public keys available for this epoch!",
        )

    if _CUR_KEY_PAIR.nonce != nonce:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Invalid nonce value!",
        )

    if not _CUR_KEY_PAIR.public_key:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"Public key is already retrieved!",
        )

    _public_key: str = _CUR_KEY_PAIR.public_key
    _CUR_KEY_PAIR.public_key = None
    _CUR_KEY_PAIR.nonce = None

    return _public_key


@validate_call
def _decrypt(ciphertext: str) -> str:

    global _KEY_PAIRS
    global _CUR_KEY_PAIR

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No more scoring available for this epoch!",
        )

    _private_key: str = _CUR_KEY_PAIR.private_key
    _CUR_KEY_PAIR = None
    _KEY_PAIRS.pop()

    # _ciphertext, _key, _iv = _extract(ciphertext=ciphertext)
    _ciphertext, _key, _iv = ("", "", "")

    _private_key: PrivateKeyTypes = serialization.load_pem_private_key(
        data=_private_key.encode()
    )
    _key_bytes: bytes = asymmetric_helper.decrypt_with_private_key(
        ciphertext=_key,
        private_key=_private_key,
        base64_decode=True,
    )

    _iv_bytes: bytes = base64.b64decode(_iv)
    _plaintext: str = symmetric_helper.decrypt_aes_cbc(
        ciphertext=_ciphertext,
        key=_key_bytes,
        iv=_iv_bytes,
        base64_decode=True,
        as_str=True,
    )

    return _plaintext


@validate_call
async def async_score(miner_output: MinerOutput) -> float:

    _score = 0.0

    try:
        _score = 0.0

        await async_copy_bot_files(miner_output=miner_output)

    except Exception as err:
        logger.error(f"Failed to evaluate the miner output: {str(err)}!")
        raise

    return _score


def build_docker(miner_output: MinerOutput, **kwargs) -> None:

    _src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
    _build_path = str(_src_dir / "bot")

    _build_args: Dict[str, str] = {}
    if miner_output.system_deps:
        _system_deps = " ".join(miner_output.system_deps)
        _build_args["APT_PACKAGES"] = _system_deps

    _image_name = "bot"
    _docker_client = docker.from_env()

    _image, _logs = _docker_client.images.build(
        path=_build_path, tag=_image_name, rm=True, buildargs=_build_args
    )

    for _log in _logs:
        if "stream" in _log:
            _log_row = _log["stream"].strip()
            logger.info(_log_row)

    _container = _docker_client.containers.run(
        image=_image, detach=True, name="bot", **kwargs
    )

    _logs = _container.logs()
    logger.info(_logs.decode())

    _container.remove(force=True)

    return


async def async_copy_bot_files(miner_output: MinerOutput) -> None:

    try:
        _src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()

        if miner_output.extra_files:
            for _extra_file_pm in miner_output.extra_files:
                _extra_file_path = str(
                    _src_dir / "bot" / "src" / "miner" / _extra_file_pm.fname
                )
                async with aiofiles.open(_extra_file_path, "w") as _extra_file:
                    await _extra_file.write(_extra_file_pm.content)

        if miner_output.requirements_txt:
            _requirements_path = str(_src_dir / "bot" / "requirements.txt")
            async with aiofiles.open(_requirements_path, "w") as _requirements_file:
                await _requirements_file.write(miner_output.requirements_txt)

        _bot_path = str(_src_dir / "bot" / "src" / "miner" / "bot.py")
        async with aiofiles.open(_bot_path, "w") as _bot_file:
            await _bot_file.write(miner_output.bot_py)

        build_docker()

    except Exception as err:
        logger.error(f"Failed to copy bot files: {str(err)}!")
        raise

    return


# def _install_packages(packages: List[str]) -> None:

#     logger.debug(f"Installing packages '{packages}'...")
#     _package: str
#     try:
#         subprocess.run(["sudo", "apt", "update"], check=True)
#         for _package in packages:
#             subprocess.run(
#                 ["sudo", "apt", "install", "-y", "--no-install-recommends", _package],
#                 check=True,
#             )

#         logger.debug(f"Successfully installed packages '{packages}'.")
#     except subprocess.CalledProcessError as err:
#         logger.error(f"Failed to install package '{_package}': {str(err)}!")

#     return


__all__ = [
    "get_task",
    "get_web",
    "get_public_key",
    "async_score",
]
