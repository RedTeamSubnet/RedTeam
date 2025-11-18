# -*- coding: utf-8 -*-

from collections import defaultdict, deque
import pathlib
import time
import docker

import threading

from typing import Deque, Optional

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

global detection_dict
detection_dict = defaultdict(list)

_driver_condition = threading.Condition()
_driver_queue: Deque[str] = deque()
_DRIVER_GRACE_SECONDS = 5


def post_driver(driver: str, request_id=None):
    driver_value = (driver or "").strip()

    with _driver_condition:
        if _driver_condition.waiters:
            _driver_queue.append(driver_value)
            _driver_condition.notify()
            pending = len(_driver_queue)
        else:
            pending = 0

    logger.info(
        f"[{request_id}] - Received driver submission '{driver_value}' (pending={pending})"
    )


def _clear_driver_queue(reason: str = "") -> None:
    with _driver_condition:
        cleared = len(_driver_queue)
        _driver_queue.clear()

    if cleared:
        logger.debug(
            f"Cleared {cleared} pending driver submissions {reason if reason else ''}".strip()
        )


def _wait_for_driver_result(
    timeout_seconds: float,
    framework_name: str,
) -> Optional[str]:
    """Wait for the next driver submission up to the provided timeout."""

    deadline = time.monotonic() + max(timeout_seconds, 0)

    with _driver_condition:
        while True:
            if _driver_queue:
                driver_value = _driver_queue.popleft() or ""
                driver_value = driver_value.strip()
                logger.info(
                    f"Matched driver submission '{driver_value}' to framework '{framework_name}'"
                )
                return driver_value or None

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            _driver_condition.wait(timeout=remaining)

    logger.warning(
        f"No driver submission received within {timeout_seconds:.1f}s for framework '{framework_name}'"
    )
    return None


def get_task() -> MinerInput:
    """Return a new challenge task."""
    return MinerInput()


@validate_call
def score(miner_output: MinerOutput) -> float:

    _score = 0.0
    global detection_dict
    detection_dict = defaultdict(list)
    _clear_driver_queue("before scoring run")

    try:
        # Copy the detection script to the templates directory
        templates_dir = str(_src_dir / "templates")

        ch_utils.copy_detector_file(
            miner_output=miner_output,
            templates_dir=templates_dir,
        )
        # Generate a randomized sequence of frameworks to test against
        random_frameworks = ch_utils.gen_ran_framework_sequence()
        docker_client = docker.from_env()

        for index, framework_entry in enumerate(random_frameworks):
            framework_image_name = framework_entry.framework_name
            framework_image = framework_entry.image
            logger.info(f"Running detection against {framework_image_name}...")

            try:
                _start_time = time.time()

                human_driver = None
                _clear_driver_queue(
                    f"before executing framework '{framework_image_name}'"
                )

                if framework_image_name == "human":
                    logger.info("Running human detection simulation...")
                    try:
                        # If human, simulate a human browser by executing pushcut shortcut
                        pushcut.execute(
                            shortcut=config.challenge.pushcut_shortcut,
                            input_url=config.challenge.pushcut_web_url,
                            timeout=config.challenge.pushcut_timeout,
                            server_id=config.challenge.pushcut_server_id,
                            api_key=config.challenge.pushcut_api_key,
                        )
                        logger.info(
                            f"Successfully executed input '{config.challenge.pushcut_web_url}' URL."
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to execute pushcut notification: {str(e)}"
                        )

                    human_driver = _wait_for_driver_result(
                        config.challenge.pushcut_timeout + _DRIVER_GRACE_SECONDS,
                        framework_image_name,
                    )
                    _end_time = time.time()
                    _execution_time = _end_time - _start_time
                    predicted_value = (
                        human_driver
                        if human_driver is not None
                        else "No driver reported"
                    )
                    detection_dict[index].append(
                        {
                            "detected": human_driver == framework_image_name,
                            "driver": framework_image_name,
                            "predicted": predicted_value,
                            "execution_time": _execution_time,
                        }
                    )
                    if human_driver == framework_image_name:
                        logger.success(
                            f"Human browser detected successfully as: {human_driver}"
                        )
                    else:
                        logger.error(
                            f"Human detection mismatch: predicted '{predicted_value}', expected '{framework_image_name}'"
                        )
                    continue

                # If not human, run the detection script in a container
                ch_utils.run_bot_container(
                    docker_client=docker_client,
                    container_name=f"{framework_image_name}",
                    network_name=f"local_network",
                    image_name=framework_image,
                    ulimit=config.challenge.docker_ulimit,
                )

                detected_driver = _wait_for_driver_result(
                    config.challenge.bot_timeout + _DRIVER_GRACE_SECONDS,
                    framework_image_name,
                )

                _end_time = time.time()
                _execution_time = _end_time - _start_time

                # Check if detection was correct
                time.sleep(1)
                if detected_driver:
                    if detected_driver == framework_image_name:
                        detection_dict[index].append(
                            {
                                "detected": True,
                                "driver": framework_image_name,
                                "predicted": detected_driver,
                                "execution_time": _execution_time,
                            }
                        )
                        logger.success(
                            f"Successfully detected driver: {detected_driver}"
                        )
                    else:
                        detection_dict[index].append(
                            {
                                "detected": False,
                                "driver": framework_image_name,
                                "predicted": detected_driver,
                                "execution_time": _execution_time,
                            }
                        )
                        logger.error(
                            f"Incorrect detection: Got {detected_driver}, expected {framework_image_name}"
                        )
                else:
                    detection_dict[index].append(
                        {
                            "detected": False,
                            "driver": framework_image_name,
                            "predicted": "The script did not return any driver",
                            "execution_time": _execution_time,
                        }
                    )
                    logger.error("No detection result found")
            except Exception as err:
                detection_dict[index].append(
                    {
                        "detected": False,
                        "driver": framework_image_name,
                        "predicted": f"Error: {str(err)}",
                        "execution_time": 0,
                    }
                )
                logger.error(
                    f"Error testing framework {framework_image_name}: {str(err)}"
                )

        logger.info("Calculating score from detection results...")

        # Reorganize results by driver type
        framework_results = defaultdict(list)
        for index in detection_dict:
            for result in detection_dict[index]:
                driver_name = result["driver"]
                framework_results[driver_name].append(result)

        for framework_name, results in framework_results.items():
            success_count = sum(1 for r in results if r["detected"])
            total_count = len(results)

            logger.info(
                f"Framework {framework_name}: {success_count} successful detections out of {total_count}"
            )

            for result in results:
                detected = result["detected"]
                predicted = result["predicted"]
                status = "Passed" if detected else "Failed"
                logger.info(
                    f"  - [{status}]: Predicted '{predicted}' for {framework_name}"
                )

        logger.info(f"Detection Results Summary:")
        for framework_name, results in framework_results.items():
            success_rate = (
                sum(1 for r in results if r["detected"]) / len(results)
                if results
                else 0
            )
            logger.info(f"- {framework_name}: {success_rate*100:.1f}% success rate")

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
    finally:
        _clear_driver_queue("after scoring run")

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
    html_response = templates.TemplateResponse(
        request=request,
        name="index.html",
    )
    return html_response


__all__ = [
    "get_task",
    "get_web",
    "score",
    "post_driver",
    "get_results",
]
