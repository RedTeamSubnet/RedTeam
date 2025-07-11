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


class TaskManager:
    """
    Task Manager for handling key pairs, action lists, and evaluation metrics
    during challenge sessions.
    """

    @validate_call
    def __init__(self, uid: str = None):
        self.uid = uid
        self.reset_tasks()
        self.action_metric_pair = {}

    def reset_tasks(self) -> None:
        """Reset all tasks, regenerate key pairs and action lists"""
        self._actions_idx = 0

        # Generate key pairs
        self.key_pairs = ch_utils.gen_key_pairs(
            n_challenge=config.challenge.n_ch_per_epoch * config.challenge.n_run_per_ch,
            key_size=config.api.security.asymmetric.key_size,
        )

        # Generate challenge actions
        self.challenges_action_list = ch_utils.gen_cb_actions(
            n_challenge=config.challenge.n_ch_per_epoch,
            window_width=config.challenge.window_width,
            window_height=config.challenge.window_height,
            n_checkboxes=config.challenge.n_checkboxes,
            min_distance=config.challenge.cb_min_distance,
            max_factor=config.challenge.cb_gen_max_factor,
            checkbox_size=config.challenge.cb_size,
            exclude_areas=config.challenge.cb_exclude_areas,
        )

        # Reset current task properties
        self.cur_key_pair = None
        self.cur_action_list = None
        self.cur_score = None
        self.action_metric_pair = {}

    def pop_task(self) -> Union[Tuple[KeyPairPM, List[Dict]], None]:
        """Get the next task (key pair and action list)"""
        if not self.key_pairs or not self.challenges_action_list:
            return None

        self.cur_key_pair = self.key_pairs.pop(0)
        self.cur_action_list = self.challenges_action_list.pop(0)

        return (self.cur_key_pair, self.cur_action_list)

    def get_next_action_list(
        self,
    ) -> List[Dict[str, Union[int, str, Dict[str, Dict[str, int]]]]]:
        """Get the next action list"""
        if not self.challenges_action_list:
            return _TMP_ACTION_LIST

        return self.challenges_action_list[self._actions_idx]

    def has_remaining_tasks(self) -> bool:
        """Check if there are remaining tasks"""
        return len(self.key_pairs) > 0 and len(self.challenges_action_list) > 0

    def get_remaining_task_count(self) -> int:
        """Get the number of remaining tasks"""
        return min(len(self.key_pairs), len(self.challenges_action_list))

    def record_metric(self, data: Dict) -> None:
        """Record a metric from the current session"""
        num_finished_sessions = len(self.action_metric_pair.keys()) + 1
        self.action_metric_pair[f"{num_finished_sessions}"] = data

    def is_last_session(self) -> bool:
        """Check if this is the last session in the epoch"""
        logger.info(f"Current session: {len(self.action_metric_pair.keys())}, ")
        return len(self.action_metric_pair.keys()) == config.challenge.n_run_per_ch

    def get_nonce(self) -> str:
        _nonce_key: str = self.cur_key_pair.public_key
        self.cur_key_pair.public_key = None
        self.cur_key_pair.nonce = None
        return _nonce_key

    def get_private_key(self) -> str:
        _private_key: str = self.cur_key_pair.private_key
        self.cur_key_pair.private_key = None
        return _private_key


# Initialize the task manager as a global variable
global tm
tm = TaskManager()


def get_task() -> MinerInput:
    """Get the task for the miner"""
    _miner_input = MinerInput()
    return _miner_input


@validate_call
def score(miner_output: MinerOutput) -> float:
    """Score the miner output"""
    _score = 0.0
    _num_tasks = config.challenge.n_ch_per_epoch * config.challenge.n_run_per_ch

    # Reset the task manager if needed
    if not tm.has_remaining_tasks():
        tm.reset_tasks()

    if tm.get_remaining_task_count() < _num_tasks:
        tm.reset_tasks()

    try:
        _container_name = "bot_container"
        if miner_output.pip_requirements:
            ch_utils.check_pip_requirements(
                pip_requirements=miner_output.pip_requirements,
                target_dt=config.challenge.allowed_pip_pkg_dt,
            )

        _build_dir = os.path.join(config.api.paths.tmp_dir, "bot")
        ch_utils.copy_bot_files(
            miner_output=miner_output,
            src_dir=str(_src_dir / "bot"),
            dst_dir=_build_dir,
        )

        _image_name = "bot:latest"
        ch_utils.build_bot_image(
            build_dir=_build_dir,
            system_deps=miner_output.system_deps,
            image_name=_image_name,
        )

        # Get the next task
        task = tm.pop_task()
        tm.cur_score = None
        if not task:
            raise BaseHTTPException(
                error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
                message=f"No initialized key pairs or action lists, or out of tasks!",
            )

        _docker_client = docker.from_env()
        ch_utils.run_bot_container(
            action_list=tm.cur_action_list,
            docker_client=_docker_client,
            image_name=_image_name,
            container_name=_container_name,
            ulimit=config.challenge.docker_ulimit,
        )

        _i = 0
        while True:
            if tm.cur_score is not None:
                _score = tm.cur_score
                tm.cur_score = None
                logger.info("Successfully scored the miner output.")
                break

            logger.info(f"Waiting for the bot to finish... {tm.cur_score is not None}")
            time.sleep(1)
            _i += 1

            if config.challenge.bot_timeout < _i:
                logger.error("Timeout error: Bot running too long or failed to finish!")
                break

    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:
    """Get the web interface for the challenge"""
    _nonce = None
    if tm.cur_key_pair:
        _nonce = tm.cur_key_pair.nonce
    else:
        _nonce = utils.gen_random_string()
        logger.warning(
            "Not initialized key pair, this endpoint is shouldn't be called directly!"
        )

    _action_list = []
    if tm.cur_action_list:
        _action_list = tm.cur_action_list
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
    """Get the random value for the nonce"""
    if not tm.cur_key_pair:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Not initialized key pair or out of key pair, this endpoint is shouldn't be called directly!",
        )

    if tm.cur_key_pair.nonce != nonce:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message=f"Invalid nonce value!",
        )

    if not tm.cur_key_pair.public_key:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.TOO_MANY_REQUESTS,
            message=f"Nonce is already retrieved!",
        )

    _nonce_key = tm.get_nonce()
    return _nonce_key


@validate_call
def eval_bot(data: str) -> None:
    """Evaluate the bot performance"""
    if not tm.cur_key_pair:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.BAD_REQUEST,
            message=f"Not initialized key pair or out of key pair, this endpoint is shouldn't be called directly!",
        )

    _private_key: str = tm.get_private_key()

    logger.debug("Evaluating the bot...")

    try:
        _plaintext = ch_utils.decrypt(ciphertext=data, private_key=_private_key)
        _plain_data = json.loads(_plaintext)

        # Record this metric
        tm.record_metric(_plain_data)

        # If this is the last session, evaluate all metrics
        if tm.is_last_session():
            _metrics_processor = MetricsProcessor(
                config={"actions": tm.cur_action_list}
            )
            _result = _metrics_processor(data=tm.action_metric_pair)
            _cur_sesion_score = _result["analysis"]["score"]

            logger.info(f"Bot evaluation result: {_result}")
            if tm.cur_score is not None:
                tm.cur_score += (
                    _cur_sesion_score / config.challenge.n_ch_per_epoch
                    if _cur_sesion_score != 0
                    else 0
                )
            else:
                tm.cur_score = (
                    _cur_sesion_score / config.challenge.n_ch_per_epoch
                    if _cur_sesion_score != 0
                    else 0
                )
            logger.info(f"Bot current score: {tm.cur_score}")

            # Reset for next epoch
            tm.action_metric_pair = {}
            tm.cur_key_pair = None
            tm.pop_task()
        else:
            tm.pop_task()
        logger.debug("Successfully evaluated the bot.")
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise

        logger.error(f"Failed to evaluate the bot: {str(err)}!")
        raise

    return


def compare_outputs(miner_input, miner_output, reference_output) -> float:
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

        _miner_code = miner_output["bot_py"]
        _reference_code = reference_output["bot_py"]

        if not _miner_code or not _reference_code:
            logger.error("Missing bot_py in miner_output or reference_output.")
            return 0.0

        comparison_result = CFGManager().compare_raw_bot_scripts(
            str_script_1=_miner_code,
            str_script_2=_reference_code,
        )

        similarity_score = comparison_result.get("similarity_score", 0.0)
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
