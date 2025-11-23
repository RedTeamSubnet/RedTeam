import time
import pathlib
import docker

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import validate_call

from api.core.exceptions import BaseHTTPException
from api.config import config
from api.endpoints.challenge.schemas import (
    MinerInput,
    MinerOutput,
    SubmissionPayloadsPM,
    TaskStatusEnum,
)
from api.endpoints.challenge import utils as ch_utils
from api.logger import logger
from api.endpoints.challenge._payload_manager import payload_manager


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()


def get_task() -> MinerInput:
    """Return a new challenge task."""
    return MinerInput()


@validate_call
def score(miner_output: MinerOutput) -> float:

    _score = 0.0
    global payload_manager
    payload_manager.restart_manager()
    _all_tasks = payload_manager.tasks

    try:
        # Copy the detection script to the templates directory
        _detections_dir = str(_src_dir / "templates" / "static" / "detections")

        ch_utils.copy_detection_files(
            miner_output=miner_output,
            detections_dir=_detections_dir,
        )

        # Generate a randomized sequence of frameworks to test against
        _docker_client = docker.from_env()

        for _framework in _all_tasks.values():
            _framework_name = str(_framework["name"])
            _framework_image = _framework["image"]
            _framework_order = _framework["order_number"]
            payload_manager.current_task = _framework

            payload_manager.update_task_status(_framework_order, TaskStatusEnum.RUNNING)
            logger.info(f"Running detection against {_framework_name}")

            try:
                _start_time = time.time()

                ch_utils.run_bot_container(
                    docker_client=_docker_client,
                    container_name=_framework_name,
                    network_name="local_network",
                    image_name=_framework_image,
                    ulimit=config.challenge.docker_ulimit,
                )
                _end_time = time.time()
                _execution_time = _end_time - _start_time

            except Exception as err:
                logger.error(
                    f"Error running detection for {_framework_name}: {str(err)}"
                )
                payload_manager.update_task_status(
                    _framework_order, TaskStatusEnum.FAILED
                )
                continue

            _bot_timeout = config.challenge.bot_timeout
            while True:
                if payload_manager.check_task_compliance(_framework_order):
                    logger.info(
                        f"Detection completed for {_framework_name} within timeout."
                    )
                    payload_manager.update_task_status(
                        _framework_order, TaskStatusEnum.COMPLETED
                    )
                    payload_manager.submitted_payloads[_framework_order][
                        "execution_time"
                    ] = _execution_time
                    ch_utils.stop_container(container_name=_framework_name)
                    break

                _bot_timeout -= 1
                if _bot_timeout <= 0:
                    logger.warning(
                        f"Detection for {_framework_name} timed out after {config.challenge.bot_timeout} seconds."
                    )
                    payload_manager.update_task_status(
                        _framework_order, TaskStatusEnum.TIMED_OUT
                    )
                    ch_utils.stop_container(container_name=_framework_name)
                    break
        _score = payload_manager.calculate_score()
        payload_manager.submitted_payloads["final_score"] = _score
        logger.info(f"Final score calculated: {_score}")

    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise
        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


def get_results() -> dict:
    global payload_manager
    logger.info("Sending detection results...")

    try:
        _submission_report = payload_manager.get_submission_report()
        if _submission_report:
            logger.info("Returning detection results")
            return _submission_report
        else:
            logger.warning("No detection results available")
            return {}

    except Exception as err:
        logger.error(f"Error retrieving results: {str(err)}")
        return {}


def submit_payload(_payload: SubmissionPayloadsPM):
    global payload_manager
    try:
        _final_results = _payload.get_final_results()
        payload_manager.submit_task(
            framework_names=_final_results,
            payload=_payload.model_dump(),
        )
    except Exception as err:
        logger.error(f"Error submitting payload: {str(err)}")
        raise


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:
    global payload_manager
    _current_task = payload_manager.current_task
    if _current_task and _current_task["order_number"]:
        _order_number = _current_task["order_number"]
    else:
        _order_number = 0
    templates = Jinja2Templates(directory=str(_src_dir / "templates"))
    _abs_result_endpoint = (
        f"http://{request.scope['server'][0]}:{config.api.port}/_payload"
    )
    logger.info(
        f"serving web page at {_abs_result_endpoint} for order number {_order_number}"
    )

    html_response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "abs_result_endpoint": _abs_result_endpoint,
            "abs_session_order_number": _order_number,
            "asb_framework_names": [
                fw.name for fw in config.challenge.framework_images
            ],
        },
    )
    return html_response


__all__ = [
    "get_task",
    "get_web",
    "score",
    "post_human_score",
    "get_results",
]
