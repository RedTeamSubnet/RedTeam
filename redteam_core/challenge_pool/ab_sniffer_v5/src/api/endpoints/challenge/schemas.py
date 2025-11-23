from pathlib import Path
from enum import Enum
from typing import Optional, Annotated, Any


from pydantic import BaseModel, Field, field_validator
from pydantic.types import StringConstraints

from api.core.constants import ALPHANUM_REGEX
from api.core import utils
from api.logger import logger
from api.config import config

_src_dir = Path(__file__).parent.parent.parent.parent.resolve()
_detection_template_dir = _src_dir / "templates" / "static" / "detections"

_detection_paths: list[Path] = list(_detection_template_dir.glob("*.js"))
_detection_files: list[dict[str, Any]] = []
_frameworks_names: list[str] = [fw.name for fw in config.challenge.framework_images]
try:
    for _detection_path in _detection_paths:
        if _detection_path.stem in _frameworks_names:
            with open(_detection_path, "r") as _detection_file:
                _detection_files.append(
                    {
                        "file_name": _detection_path.name,
                        "content": _detection_file.read(),
                    }
                )

except Exception:
    logger.exception(f"Failed to read detection files in detections folder!")


class TaskStatusEnum(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class MinerInput(BaseModel):
    random_val: Optional[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=4,
                max_length=64,
                pattern=ALPHANUM_REGEX,
            ),
        ]
    ] = Field(
        default_factory=utils.gen_random_string,
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class DetectionFilePM(BaseModel):
    file_name: str = Field(
        ...,
        min_length=4,
        max_length=64,
        title="File Name",
        description="Name of the file.",
        examples=["detect.js"],
    )
    content: str = Field(
        ...,
        min_length=2,
        title="File Content",
        description="Content of the file as a string.",
        examples=["console.log('browser');"],
    )


class MinerOutput(BaseModel):
    detection_files: list[DetectionFilePM] = Field(
        ...,
        title="Detection JS Files",
        description="List of detection JS files for the challenge.",
        examples=[_detection_files],
    )

    @field_validator("detection_files", mode="after")
    @classmethod
    def _check_detection_files(
        cls, val: list[DetectionFilePM]
    ) -> list[DetectionFilePM]:
        if len(val) != len(_frameworks_names):
            raise ValueError(
                f"Number of submitted detection files ({len(val)}) does not match the expected number ({len(_frameworks_names)})!"
            )

        for _miner_file_pm in val:

            if _miner_file_pm.file_name.split(".")[-1] != "js":
                raise ValueError("File should be a JavaScript (.js) file!")

            if _miner_file_pm.file_name.split(".")[0] not in _frameworks_names:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` is not a valid detection file name!"
                )

            file_names = [df.file_name for df in val]
            if file_names.count(_miner_file_pm.file_name) > 1:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` detection file is duplicated in the submission!"
                )

            _content_lines = _miner_file_pm.content.splitlines()
            if len(_content_lines) > 500:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file contains too many lines, should be <= 500 lines!"
                )

        return val


class PayloadPM(BaseModel):
    detected: bool = Field(
        ...,
        title="Driver Detected",
        description="Indicates whether the driver was detected.",
        examples=[True],
    )
    raw: Optional[bool] = Field(
        None,
        title="Raw Detection",
        description="Indicates whether the detection was raw.",
        examples=[False],
    )
    framework_name: Optional[str] = Field(
        None,
        title="Automation framework name",
        description="Name of the automation framework.",
        examples=["nodriver"],
    )
    model_config = {
        "extra": "forbid",
    }


class SubmissionPayloadsPM(BaseModel):
    results: list[PayloadPM] = Field(
        ...,
        title="Detection Results",
        description="Detection results submitted by the miner.",
        examples=[
            [
                {
                    "detected": True,
                    "raw": True,
                    "framework_name": "nodriver",
                }
            ]
        ],
    )
    order_number: int = Field(
        ...,
        title="Submission Order Number",
        description="Order number of the submission.",
        examples=[0],
    )
    model_config = {
        "extra": "forbid",
    }

    @field_validator("results", mode="after")
    @classmethod
    def _check_results(cls, val: list[PayloadPM]) -> list[PayloadPM]:
        if len(val) != len(_frameworks_names):
            raise ValueError(
                f"Number of submitted results ({len(val)}) does not match the expected number ({len(_frameworks_names)})!"
            )

        return val

    def get_final_results(self) -> list[str]:
        """Returns a list of detected=True framework names."""
        final_result: list[str] = []
        for result in self.results:
            if result.detected:
                final_result.append(result.framework_name or "unknown")
        return final_result


__all__ = [
    "MinerInput",
    "DetectionFilePM",
    "MinerOutput",
    "PayloadPM",
    "SubmissionPayloadsPM",
    "TaskStatusEnum",
]
