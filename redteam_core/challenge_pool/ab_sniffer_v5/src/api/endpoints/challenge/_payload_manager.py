import random

from pydantic import validate_call
from api.config import config
from api.logger import logger
from api.endpoints.challenge.schemas import TaskStatusEnum


class PayloadManager:
    @validate_call
    def __init__(self):
        self.tasks: dict[int, dict] = {}
        self.current_task: dict | None = None
        self.submitted_payloads: dict[int, dict] = {}
        self.expected_order: dict[int, str] = {}
        self.score: float = 0.0

        self.gen_ran_framework_sequence()
        return

    def restart_manager(self) -> None:
        self.tasks = {}
        self.current_task = None
        self.submitted_payloads = {}
        self.expected_order = {}
        self.score = 0.0

        self.gen_ran_framework_sequence()
        return

    def submit_task(self, framework_names: list[str], payload: dict) -> None:
        try:
            _expected_fm = self.expected_order[payload["order_number"]]
            _is_detected = _expected_fm in framework_names
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
            if submission["expected_framework"] == "human" and (
                submission["collided"] or not submission["detected"]
            ):
                logger.warning("Couldn't detect human correctly, score is zero")
                return 0.0

        _correct_detections = sum(
            1 if not submission["collided"] else 0.1
            for submission in self.submitted_payloads.values()
            if submission["detected"]
        )

        if _total_tasks == 0:
            logger.warning("No tasks found, score is zero")
            return 0.0

        self.score = _correct_detections / _total_tasks
        return self.score

    def gen_ran_framework_sequence(self) -> None:
        frameworks = config.challenge.framework_images
        repeated_frameworks = []

        for _ in range(config.challenge.repeated_framework_count):
            repeated_frameworks.extend(frameworks)

        random.shuffle(repeated_frameworks)

        for _index, _framework in enumerate(repeated_frameworks):
            _framework = _framework.model_dump()
            self.expected_order[_index] = _framework["name"]
            _framework["order_number"] = _index
            _framework["status"] = TaskStatusEnum.CREATED
            self.tasks[_index] = _framework

        return

    def update_task_status(self, order_number: int, new_status: TaskStatusEnum):
        if self.tasks[order_number] and self.tasks[order_number]["status"]:
            self.tasks[order_number]["status"] = new_status
        else:
            logger.error(
                f"Couldn't update status of task with order_number: {order_number}"
            )

    def check_task_compliance(self, order_number: int) -> bool:
        if order_number in self.submitted_payloads:
            return True
        return False

    def get_submission_report(self) -> dict[int, dict]:
        return self.submitted_payloads


payload_manager = PayloadManager()

__all__ = [
    "PayloadManager",
    "payload_manager",
]
