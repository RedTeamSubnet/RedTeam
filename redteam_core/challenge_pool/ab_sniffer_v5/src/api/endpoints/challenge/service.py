import time
import pathlib
from collections import defaultdict

import docker
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import validate_call

from api.core.exceptions import BaseHTTPException
from api.config import config
from api.endpoints.challenge.schemas import MinerInput, MinerOutput
from api.endpoints.challenge import utils as ch_utils
from api.logger import logger


# Define source directory - the root of the project
_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()

# Initialize global variable for human verification
global human_req_val
human_req_val = ""  # Default to empty string

global detection_dict
detection_dict = defaultdict(list)


def post_human_score(drivers: str, request_id=None):
    global human_req_val
    human_req_val = drivers
    logger.info(f"Received human verification input: {human_req_val}")


def get_task() -> MinerInput:
    """Return a new challenge task."""
    return MinerInput()


@validate_call
def score(miner_output: MinerOutput) -> float:

    _score = 0.0
    global detection_dict
    detection_dict = defaultdict(list)  # Reset for new evaluation

    try:
        # Copy the detection script to the templates directory
        _detections_dir = str(_src_dir / "templates" / "static" / "detections")

        ch_utils.copy_detection_files(
            miner_output=miner_output,
            detections_dir=_detections_dir,
        )

        # Generate a randomized sequence of frameworks to test against
        _target_frameworks = ch_utils.gen_framework_sequence()
        _docker_client = docker.from_env()

        for _index, _framework in enumerate(_target_frameworks):
            _framework_name = _framework.name
            _framework_image = _framework.image
            logger.info(f"Running detection against {_framework_name}...")

            try:
                _start_time = time.time()

                _detected_driver = ch_utils.run_bot_container(
                    docker_client=_docker_client,
                    container_name=f"{_framework_name}",
                    network_name=f"local_network",
                    image_name=_framework_image,
                    ulimit=config.challenge.docker_ulimit,
                )
                _end_time = time.time()
                _execution_time = _end_time - _start_time
            except Exception as err:
                logger.error(
                    f"Error running detection for {_framework_name}: {str(err)}"
                )
                _detected_driver = "error"
                _execution_time = None
    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise
        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


def get_results() -> dict:
    global detection_dict
    logger.info("Sending detection results...")

    try:
        if detection_dict:
            logger.info("Returning detection results")
            return detection_dict
        else:
            logger.warning("No detection results available")
            return {}

    except Exception as err:
        logger.error(f"Error retrieving results: {str(err)}")
        return {}


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:
    templates = Jinja2Templates(directory=str(_src_dir / "templates"))
    _abs_result_endpoint = str(config.challenge.result_endpoint)

    html_response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "abs_result_endpoint": _abs_result_endpoint,
            "abs_session_order_number": 0,
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
