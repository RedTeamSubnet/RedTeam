# -*- coding: utf-8 -*-

import os
import time
import json
import pathlib
from typing import List, Union, Dict, Tuple

import docker
from pydantic import validate_call
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from cfg_analyser import CFGManager

try:
    from modules.rt_hb_score import MetricsProcessor  # type: ignore
except ImportError:
    from rt_hb_score import MetricsProcessor  # type: ignore

from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.config import config
from api.core.exceptions import BaseHTTPException
from api.helpers.crypto import asymmetric as asymmetric_helper
from api.endpoints.challenge.schemas import KeyPairPM, MinerInput, MinerOutput
from api.endpoints.challenge import utils as ch_utils
from api.logger import logger


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()


_TMP_ACTION_LIST: List[Dict[str, Union[int, str, Dict[str, Dict[str, int]]]]] = (
    ch_utils.gen_cb_actions(
        n_challenge=1,
        window_width=config.challenge.window_width,
        window_height=config.challenge.window_height,
        n_checkboxes=config.challenge.n_checkboxes,
        min_distance=config.challenge.cb_min_distance,
        max_factor=config.challenge.cb_gen_max_factor,
        checkbox_size=config.challenge.cb_size,
        exclude_areas=config.challenge.cb_exclude_areas,
    )[0]
)

_KEY_PAIRS: List[KeyPairPM] = ch_utils.gen_key_pairs(
    n_challenge=config.challenge.n_ch_per_epoch,
    key_size=config.api.security.asymmetric.key_size,
)
_CUR_KEY_PAIR: Union[KeyPairPM, None] = None
_CUR_SCORE: Union[float, None] = None
_CHALLENGES_ACTION_LIST: List[
    List[Dict[str, Union[int, str, Dict[str, Dict[str, int]]]]]
] = ch_utils.gen_cb_actions(
    n_challenge=config.challenge.n_ch_per_epoch,
    window_width=config.challenge.window_width,
    window_height=config.challenge.window_height,
    n_checkboxes=config.challenge.n_checkboxes,
    min_distance=config.challenge.cb_min_distance,
    max_factor=config.challenge.cb_gen_max_factor,
    checkbox_size=config.challenge.cb_size,
    exclude_areas=config.challenge.cb_exclude_areas,
    pre_action_list=config.challenge.cb_pre_action_list,
)
_CUR_ACTION_LIST: Union[
    List[Dict[str, Union[int, str, Dict[str, Dict[str, int]]]]], None
] = None


def get_task() -> MinerInput:

    _miner_input = MinerInput()
    return _miner_input


@validate_call
def score(miner_output: MinerOutput, reset: bool) -> float:

    global _KEY_PAIRS
    global _CHALLENGES_ACTION_LIST
    global _CUR_KEY_PAIR
    global _CUR_ACTION_LIST
    global _CUR_SCORE

    _container_name = "bot_container"
    ch_utils.stop_container(container_name=_container_name)

    if reset:
        _KEY_PAIRS = ch_utils.gen_key_pairs(
            n_challenge=config.challenge.n_ch_per_epoch,
            key_size=config.api.security.asymmetric.key_size,
        )

        _CHALLENGES_ACTION_LIST = ch_utils.gen_cb_actions(
            n_challenge=config.challenge.n_ch_per_epoch,
            window_width=config.challenge.window_width,
            window_height=config.challenge.window_height,
            n_checkboxes=config.challenge.n_checkboxes,
            min_distance=config.challenge.cb_min_distance,
            max_factor=config.challenge.cb_gen_max_factor,
            checkbox_size=config.challenge.cb_size,
            exclude_areas=config.challenge.cb_exclude_areas,
            pre_action_list=config.challenge.cb_pre_action_list,
        )

    if not _KEY_PAIRS:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No initialized key pairs or out of key pairs, this endpoint is shouldn't be called directly!",
        )

    if not _CHALLENGES_ACTION_LIST:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"No initialized action lists or out of action lists, this endpoint is shouldn't be called directly!",
        )

    _CUR_KEY_PAIR = _KEY_PAIRS.pop(0)
    _CUR_ACTION_LIST = _CHALLENGES_ACTION_LIST.pop(0)
    _CUR_SCORE = None

    logger.debug(f"Current action list: {_CUR_ACTION_LIST}")

    _score = 0.0

    logger.debug("Scoring the miner output...")
    try:
        if miner_output.pip_requirements:
            ch_utils.check_pip_requirements(
                pip_requirements=miner_output.pip_requirements,
                target_dt=config.challenge.allowed_pip_pkg_dt,
            )

        _build_dir = os.path.join(config.api.paths.tmp_dir, "bot")
        ch_utils.copy_bot_files(
            miner_output=miner_output, src_dir=str(_src_dir / "bot"), dst_dir=_build_dir
        )

        _docker_client = docker.from_env()
        _image_name = "bot:latest"
        ch_utils.build_bot_image(
            docker_client=_docker_client,
            build_dir=_build_dir,
            system_deps=miner_output.system_deps,
            image_name=_image_name,
        )
        ch_utils.run_bot_container(
            docker_client=_docker_client,
            action_list=_CUR_ACTION_LIST,
            image_name=_image_name,
            container_name=_container_name,
            ulimit=config.challenge.docker_ulimit,
        )

        _i = 0
        while True:
            if _CUR_SCORE is not None:
                _score = _CUR_SCORE
                _CUR_SCORE = None
                break

            logger.debug("Waiting for the bot to finish...")
            time.sleep(1)
            _i += 1

            if config.challenge.bot_timeout < _i:
                raise BaseHTTPException(
                    error_enum=ErrorCodeEnum.BAD_REQUEST,
                    message=f"Timeout error: Bot running too long or failed to finish!",
                )

        logger.debug("Successfully scored the miner output.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:

    _nonce = None
    if _CUR_KEY_PAIR:
        _nonce = _CUR_KEY_PAIR.nonce
    else:
        _nonce = utils.gen_random_string()
        logger.warning(
            "Not initialized key pair, this endpoint is shouldn't be called directly!"
        )

    _action_list = []
    if _CUR_ACTION_LIST:
        _action_list = _CUR_ACTION_LIST
    else:
        _action_list = _TMP_ACTION_LIST
        logger.warning(
            "Not initialized action list, this endpoint is shouldn't be called directly!"
        )

    _key_pair: Tuple[str, str] = asymmetric_helper.gen_key_pair(
        key_size=config.api.security.asymmetric.key_size, as_str=True
    )
    _, _public_key = _key_pair
    _templates = Jinja2Templates(directory=(_src_dir / "./templates/html"))
    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "nonce": _nonce,
            "public_key": _public_key,
            "actions_list": _action_list,
        },
    )
    return _html_response


@validate_call
def get_random_val(nonce: str) -> str:

    global _CUR_KEY_PAIR

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Not initialized key pair or out of key pair, this endpoint is shouldn't be called directly!",
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
def eval_bot(data: str) -> None:

    global _CUR_KEY_PAIR
    global _CUR_ACTION_LIST
    global _CUR_SCORE

    if not _CUR_KEY_PAIR:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Not initialized key pair or out of key pair, this endpoint is shouldn't be called directly!",
        )

    if not _CUR_ACTION_LIST:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Not initialized action list or out of action list, this endpoint is shouldn't be called directly!",
        )

    _private_key: str = _CUR_KEY_PAIR.private_key
    _CUR_KEY_PAIR = None

    logger.debug("Evaluating the bot...")
    try:
        _plaintext = ch_utils.decrypt(ciphertext=data, private_key=_private_key)

        _metrics_processor = MetricsProcessor(config={"actions": _CUR_ACTION_LIST})
        _plain_data = json.loads(_plaintext)
        _result = _metrics_processor(data=_plain_data)
        _CUR_ACTION_LIST = None
        logger.info(f"Bot evaluation result: {_result}")
        _CUR_SCORE = _result["analysis"]["score"]
        logger.info(f"Bot score: {_CUR_SCORE}")

        logger.debug("Successfully evaluated the bot.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to evaluate the bot: {str(err)}!")
        raise

    return


@validate_call
def compare_outputs(
    miner_input: MinerInput, miner_output: MinerOutput, reference_output: MinerOutput
) -> float:
    """
    Compare miner's output against a reference output using CFGAnalyser and CFGComparer.

    Args:
        miner_input (dict): The input used for both miner outputs.
        miner_output (dict): The output from the current miner (expects "bot_py" key).
        reference_output (dict): The reference output.

    Returns:
        float: Similarity score between 0 and 1.
    """
    try:
        logger.info("Analyzing miner output...")

        miner_code = miner_output.bot_py
        reference_code = reference_output.bot_py

        if not miner_code or not reference_code:
            logger.error("Missing bot_py in miner_output or reference_output.")
            return 0.0

        comparison_result = CFGManager().run_raw_scripts_comparison(
            str_script_1=miner_code,
            str_script_2=reference_code,
        )

        similarity_score = comparison_result.get("maximum_similarity", 0.0)
        logger.info(f"Computed similarity score: {similarity_score}")

        return max(0.0, min(1.0, similarity_score))

    except Exception as err:
        logger.error(f"Error in compare_outputs function: {str(err)}")
        return 0.0


__all__ = [
    "get_task",
    "get_web",
    "get_random_val",
    "score",
    "eval_bot",
    "compare_outputs",
]
