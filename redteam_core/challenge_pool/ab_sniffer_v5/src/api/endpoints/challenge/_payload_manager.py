import random

from pydantic import validate_call
from api.config import config
from api.logger import logger


class PayloadManager:
    @validate_call
    def __init__(self):
        self.tasks = []
        self.current_task = None
        self.submitted_payloads = {}
        self.expected_order = {}
        self.score = 0.0

        self.gen_ran_framework_sequence()

    def get_task(self) -> dict:
        if self.tasks:
            self.current_task = self.tasks.pop(0)
            return self.current_task
        else:
            raise RuntimeError("No more tasks available!")

    def get_current_task(self) -> dict:
        return self.current_task

    def submit_task(self, framework_names: list[str], payload: dict) -> None:
        try:
            _expected_fm = self.expected_order[payload["order_number"]]
            _is_detected = framework_names in _expected_fm
            _is_collided = len(framework_names) > 1

            if _expected_fm == "human":
                _is_detected = True if len(framework_names) == 0 else False
                _is_collided = True if len(framework_names) > 0 else False

            self.submitted_payloads[payload["order_number"]] = {
                "expected_framework": _expected_fm,
                "submitted_framework": framework_names,
                "detected": _is_detected,
                "collided": _is_collided,
            }
        except Exception as err:
            logger.error(f"Failed to add submitted payload: {err}!")
            raise
        return

    def calculate_score(self) -> float:
        _total_tasks = len(self.expected_order)
        # check no collision with human
        for submission in self.submitted_payloads.values():
            if submission["expected_framework"] == "human" and submission["collided"]:
                return 0.0

        _correct_detections = sum(
            1
            for submission in self.submitted_payloads.values()
            if submission["detected"] and not submission["collided"]
        )

        if _total_tasks == 0:
            return 0.0

        self.score = _correct_detections / _total_tasks
        return self.score

    def get_received_order_numbers(self) -> list[int]:
        return list(self.submitted_payloads.keys())

    def gen_ran_framework_sequence(self) -> None:
        frameworks = config.challenge.framework_images
        repeated_frameworks = []

        for _ in range(config.challenge.repeated_framework_count):
            repeated_frameworks.extend(frameworks)

        random.shuffle(repeated_frameworks)

        for _index, _framework in enumerate(repeated_frameworks):
            self.expected_order[_index] = _framework["name"]
            _framework["order"] = _index
            self.tasks.append(_framework)

        return
