# -*- coding: utf-8 -*-

import os
import random
from typing import List, Dict, Union, Tuple

import docker
from docker import DockerClient
from pydantic import validate_call

from api.core import utils
from api.helpers.crypto import asymmetric as asymmetric_helper
from api.endpoints.challenge.schemas import KeyPairPM, MinerOutput
from api.logger import logger


@validate_call
def gen_key_pairs(n_challenge: int, key_size: int) -> List[KeyPairPM]:

    _key_pairs: List[KeyPairPM] = []
    for _ in range(n_challenge):
        _key_pair: Tuple[str, str] = asymmetric_helper.gen_key_pair(
            key_size=key_size, as_str=True
        )
        _private_key, _public_key = _key_pair
        _nonce = utils.gen_random_string(length=32)
        _key_pair_pm = KeyPairPM(
            private_key=_private_key, public_key=_public_key, nonce=_nonce
        )
        _key_pairs.append(_key_pair_pm)

    return _key_pairs


@validate_call
def gen_cb_positions(
    window_width: int = 1920,
    window_height: int = 1080,
    n_checkboxes: int = 5,
    min_distance: int = 300,
    max_attempts_factor: int = 10,
    checkbox_size: int = 20,  # Assuming checkbox size ~20px
    exclude_areas: Union[List[Dict[int, int]], None] = None,
) -> List[Dict[str, int]]:

    _positions = []
    _max_attempts = n_checkboxes * max_attempts_factor  # Avoid infinite loops

    _attempts = 0
    while len(_positions) < n_checkboxes:
        _x = random.randint(0, window_width - checkbox_size)
        _y = random.randint(0, window_height - checkbox_size)

        _is_near = False
        for _pos in _positions:
            ## Calculate distance between two points using Euclidean distance:
            if (_x - _pos["x"]) ** 2 + (_y - _pos["y"]) ** 2 < min_distance**2:
                _is_near = True
                break

        _is_in_area = False
        if exclude_areas:
            for _area in exclude_areas:
                if (_area["x1"] <= _x <= _area["x2"]) and (
                    _area["y1"] <= _y <= _area["y2"]
                ):
                    _is_in_area = True
                    break

        if (not _is_near) and (not _is_in_area):
            _position = {"x": _x, "y": _y}
            _positions.append(_position)

        _attempts += 1

        if _max_attempts <= _attempts:
            logger.warning("Skipped generating positions due to max attempts!")
            break

    return _positions


@validate_call
def copy_bot_files(miner_output: MinerOutput, src_dir: str) -> None:

    logger.info("Copying bot files...")
    try:
        _bot_dir = os.path.join(src_dir, "bot")
        _bot_core_dir = os.path.join(_bot_dir, "src", "core")

        # if miner_output.extra_files:
        #     for _extra_file_pm in miner_output.extra_files:
        #         _extra_file_path = os.path.join(_bot_core_dir, _extra_file_pm.fname)
        #         with open(_extra_file_path, "w") as _extra_file:
        #             _extra_file.write(_extra_file_pm.content)

        if miner_output.requirements_txt:
            _requirements_path = os.path.join(_bot_dir, "requirements.txt")
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
def build_bot_image(
    docker_client: DockerClient,
    build_dir: str,
    miner_output: MinerOutput,
    image_name: str = "bot:latest",
) -> None:

    logger.info("Building bot docker image...")
    try:
        _kwargs = {}
        if miner_output.system_deps:
            _kwargs["buildargs"] = {"APT_PACKAGES": miner_output.system_deps}

        _, _logs = docker_client.images.build(
            path=build_dir, tag=image_name, rm=True, **_kwargs
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
def run_bot_container(
    docker_client: DockerClient,
    image_name: str = "bot:latest",
    container_name: str = "bot_container",
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


__all__ = [
    "gen_key_pairs",
    "gen_cb_positions",
    "copy_bot_files",
    "build_bot_image",
    "run_bot_container",
]
