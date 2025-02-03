# -*- coding: utf-8 -*-

import base64
import pathlib
from typing import List, Tuple, Union

import docker
from docker import DockerClient
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


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_bot_dir = _src_dir / "bot"


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


@validate_call
def _copy_bot_files(miner_output: MinerOutput) -> None:

    logger.info("Copying bot files...")
    try:
        _bot_core_dir = _src_dir / "bot" / "src" / "core"

        if miner_output.extra_files:
            for _extra_file_pm in miner_output.extra_files:
                _extra_file_path = str(_bot_core_dir / _extra_file_pm.fname)
                with open(_extra_file_path, "w") as _extra_file:
                    _extra_file.write(_extra_file_pm.content)

        if miner_output.requirements_txt:
            _requirements_path = str(_bot_dir / "requirements.txt")
            with open(_requirements_path, "w") as _requirements_file:
                _requirements_file.write(miner_output.requirements_txt)

        _bot_path = str(_bot_core_dir / "bot.py")
        with open(_bot_path, "w") as _bot_file:
            _bot_file.write(miner_output.bot_py)

        logger.success("Successfully copied bot files.")
    except Exception as err:
        logger.error(f"Failed to copy bot files: {str(err)}!")
        raise

    return


@validate_call(config={"arbitrary_types_allowed": True})
def _build_bot_image(
    docker_client: DockerClient, miner_output: MinerOutput, image_name: str = "bot"
) -> None:

    logger.info("Building bot docker image...")
    try:
        _build_path = str(_bot_dir)

        _kwargs = {}
        if miner_output.system_deps:
            _kwargs["buildargs"] = {"APT_PACKAGES": miner_output.system_deps}

        _, _logs = docker_client.images.build(
            path=_build_path, tag=image_name, rm=True, **_kwargs
        )

        for _log in _logs:
            if "stream" in _log:
                _log_stream = _log["stream"].strip()
                logger.info(_log_stream)

        logger.success("Successfully built bot docker image.")
    except Exception as err:
        logger.error(f"Failed to build bot docker: {str(err)}!")
        raise

    return


@validate_call(config={"arbitrary_types_allowed": True})
def _run_bot_container(
    docker_client: DockerClient,
    container_name: str = "bot",
    image_name: str = "bot",
    **kwargs,
) -> None:

    logger.info("Running bot docker container...")
    try:
        _ulimit_nofile = docker.types.Ulimit(name="nofile", soft=32768, hard=32768)
        _container = docker_client.containers.run(
            image=image_name,
            name=container_name,
            detach=True,
            auto_remove=True,
            ulimits=[_ulimit_nofile],
            environment={"TZ": "UTC"},
            **kwargs,
        )

        for _log in _container.logs(stream=True):
            logger.info(_log.decode().strip())

        logger.info(
            f"Container '{_container.name}' exited with code - {_container.wait()}."
        )
        logger.info("Successfully ran bot docker container.")
    except Exception as err:
        logger.error(f"Failed to run bot docker: {str(err)}!")
        raise

    return


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
            error_enum=ErrorCodeEnum.BAD_REQUEST,
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
        _docker_client = docker.from_env()
        _image_name = "bot"
        _container_name = "bot"

        _copy_bot_files(miner_output=miner_output)
        _build_bot_image(
            docker_client=_docker_client,
            miner_output=miner_output,
            image_name=_image_name,
        )
        _run_bot_container(
            docker_client=_docker_client,
            container_name=_container_name,
            image_name=_image_name,
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
