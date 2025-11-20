import os
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
from api.helpers.pushcut import Pushcut
from api.logger import logger


# Define source directory - the root of the project
_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
pushcut = Pushcut(api_key=config.challenge.pushcut_api_key)

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

                # if _framework_name == "human":
                #     logger.info("Running human detection simulation...")
                #     try:

                #         logger.info(
                #             f"Successfully executed input '{config.challenge.pushcut_web_url}' URL."
                #         )
                #     except Exception as e:
                #         logger.error(
                #             f"Failed to execute pushcut notification: {str(e)}"
                #         )

                #     _end_time = time.time()
                #     _execution_time = _end_time - _start_time
                #     detection_dict[_index].append(
                #         {
                #             "detected": human_req_val == _framework_name,
                #             "driver": _framework_name,
                #             "predicted": human_req_val,
                #             "execution_time": _execution_time,
                #         }
                #     )
                #     logger.success(
                #         f"Human browser detected successfully as: {human_req_val}"
                #     )
                #     continue

                _detected_driver = ch_utils.run_bot_container(
                    docker_client=_docker_client,
                    container_name=f"{_framework_name}",
                    network_name=f"local_network",
                    image_name=_framework_image,
                    ulimit=config.challenge.docker_ulimit,
                )
                _end_time = time.time()
                _execution_time = _end_time - _start_time

                # Check if detection was correct
                time.sleep(1)
                if _detected_driver:
                    if _detected_driver == _framework_name:
                        detection_dict[_index].append(
                            {
                                "detected": True,
                                "driver": _framework_name,
                                "predicted": _detected_driver,
                                "execution_time": _execution_time,
                            }
                        )
                        logger.success(
                            f"Successfully detected driver: {_detected_driver}"
                        )
                    else:
                        detection_dict[_index].append(
                            {
                                "detected": False,
                                "driver": _framework_name,
                                "predicted": _detected_driver,
                                "execution_time": _execution_time,
                            }
                        )
                        logger.error(
                            f"Incorrect detection: Got {_detected_driver}, expected {_framework_name}"
                        )
                else:
                    detection_dict[_index].append(
                        {
                            "detected": False,
                            "driver": _framework_name,
                            "predicted": "The script did not return any driver",
                            "execution_time": _execution_time,
                        }
                    )
                    logger.error("No detection result found")
            except Exception as err:
                detection_dict[_index].append(
                    {
                        "detected": False,
                        "driver": _framework_name,
                        "predicted": f"Error: {str(err)}",
                        "execution_time": 0,
                    }
                )
                logger.error(f"Error testing framework {_framework_name}: {str(err)}")

        logger.info("Calculating score from detection results...")

        # Reorganize results by driver type
        framework_results = defaultdict(list)
        for _index in detection_dict:
            for result in detection_dict[_index]:
                driver_name = result["driver"]
                framework_results[driver_name].append(result)

        for _framework_name, results in framework_results.items():
            success_count = sum(1 for r in results if r["detected"])
            total_count = len(results)

            logger.info(
                f"Framework {_framework_name}: {success_count} successful detections out of {total_count}"
            )

            for result in results:
                detected = result["detected"]
                predicted = result["predicted"]
                status = "Passed" if detected else "Failed"
                logger.info(
                    f"  - [{status}]: Predicted '{predicted}' for {_framework_name}"
                )

        logger.info(f"Detection Results Summary:")
        for _framework_name, results in framework_results.items():
            success_rate = (
                sum(1 for r in results if r["detected"]) / len(results)
                if results
                else 0
            )
            logger.info(f"- {_framework_name}: {success_rate*100:.1f}% success rate")

        # Calculate the actual score based on detection results
        total_detections = 0
        successful_detections = 0
        for results in framework_results.values():
            for result in results:
                total_detections += 1
                if result["detected"]:
                    successful_detections += 1
        _score = (
            successful_detections / total_detections if total_detections > 0 else 0.0
        )
        logger.info(
            f"Final score: {_score} ({successful_detections}/{total_detections} successful detections)"
        )

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
        context={"abs_result_endpoint": _abs_result_endpoint},
    )
    return html_response


__all__ = [
    "get_task",
    "get_web",
    "score",
    "post_human_score",
    "get_results",
]
