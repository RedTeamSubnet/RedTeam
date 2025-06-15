# -*- coding: utf-8 -*-

from collections import defaultdict
import pathlib
import time
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
from cfg_analyser import CFGManager

# Define source directory - the root of the project
_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()


def get_task() -> MinerInput:
    """Return a new challenge task."""
    return MinerInput()


@validate_call
def score(miner_output: MinerOutput) -> float:

    _score = 0.0
    detection_dict = defaultdict(dict)

    try:
        # Copy the detection script to the templates directory
        templates_dir = str(_src_dir / "templates")

        ch_utils.copy_detector_file(
            miner_output=miner_output,
            templates_dir=templates_dir,
        )
        format_status = ch_utils.check_format_error(templates_dir=templates_dir)

        if not format_status:
            logger.warning(
                "Submitted miner submission could not pass format check. Getting null score"
            )
            return None
        _submission_size = ch_utils.get_submission_file_size(
            templates_dir=templates_dir
        )
        # Generate a randomized sequence of frameworks to test against
        random_frameworks = ch_utils.gen_ran_framework_sequence()
        docker_client = docker.from_env()

        # Test against each framework
        for framework_image_name, framework_image in random_frameworks:
            framework_image = framework_image[1]
            framework_image_name = framework_image_name[1]

            logger.info(f"Running detection against {framework_image_name}...")

            try:
                # Run container and get detected driver type
                _start_time = time.time()
                detected_driver = ch_utils.run_bot_container(
                    docker_client=docker_client,
                    container_name=f"{framework_image_name}",
                    network_name=f"local_network",
                    image_name=framework_image,
                    ulimit=config.challenge.docker_ulimit,
                )
                _end_time = time.time()
                _execution_time = _end_time - _start_time

                # Check if detection was correct
                time.sleep(1)
                if detected_driver:
                    if detected_driver == framework_image_name:
                        if framework_image_name not in detection_dict:
                            detection_dict[framework_image_name] = []
                        detection_dict[framework_image_name].append(
                            {"detected": True, "execution_time": _execution_time}
                        )
                        logger.success(
                            f"Successfully detected driver: {detected_driver}"
                        )
                else:
                    if framework_image_name not in detection_dict:
                        detection_dict[framework_image_name] = []
                    detection_dict[framework_image_name].append(
                        {"detected": False, "execution_time": _execution_time}
                    )
                    logger.error("No detection result found")
            except Exception as err:
                logger.error(f"Error testing framework {framework_image}: {str(err)}")

            _score = 0
            for framework in detection_dict.keys():
                _detect_count = 0
                for detection_results in detection_dict[framework]:
                    if detection_results["detected"]:
                        _detect_count += 1
                if _detect_count == config.challenge.repeated_framework_count:
                    _score += 1 / config.challenge.framework_count

        logger.info(f"Final score: {_score}")

    except Exception as err:
        if isinstance(err, BaseHTTPException):
            raise
        logger.error(f"Failed to score the miner output: {str(err)}!")
        raise

    return _score


@validate_call(config={"arbitrary_types_allowed": True})
def get_web(request: Request) -> HTMLResponse:
    templates = Jinja2Templates(directory=str(_src_dir / "templates"))
    html_response = templates.TemplateResponse(
        request=request,
        name="index.html",
    )
    return html_response


def compare_outputs(miner_input, miner_output, reference_output) -> float:
    """
    Compare miner's output against a reference output using CFGAnalyser and CFGComparer.

    Args:
        miner_input (dict): The input used for both miner outputs.
        miner_output (dict): The output from the current miner (expects "detection_js" key).
        reference_output (dict): The reference output.

    Returns:
        float: Similarity score between 0 and 1.
    """
    try:
        logger.info("Analyzing miner output...")

        miner_code = miner_output["detection_js"]
        reference_code = reference_output["detection_js"]

        if not miner_code or not reference_code:
            logger.error("Missing detection_js in miner_output or reference_output.")
            return 0.0

        comparison_result = CFGManager().compare_raw_scripts(
            str_script_1=miner_code, str_script_2=reference_code
        )

        similarity_score = comparison_result.get("similarity_score", 0.0)
        logger.info(f"Similarity Score: {similarity_score}")
        logger.info(f"Comparison Result: {comparison_result}")

        try:
            similarity_score = float(similarity_score)
        except Exception:
            similarity_score = 0.0

        return max(0.0, min(1.0, similarity_score))

    except Exception as err:
        logger.error(f"Error in compare_outputs function: {str(err)}")
        return 0.0


__all__ = [
    "get_task",
    "get_web",
    "compare_outputs",
    "score",
]
