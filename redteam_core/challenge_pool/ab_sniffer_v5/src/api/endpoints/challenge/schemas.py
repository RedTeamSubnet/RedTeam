from pathlib import Path
from typing import Optional, Annotated, Any

from pydantic import BaseModel, Field, field_validator
from pydantic.types import StringConstraints

from api.core.constants import ALPHANUM_REGEX
from api.core import utils
from api.logger import logger


_src_dir = Path(__file__).parent.parent.parent.parent.resolve()
_detection_template_dir = _src_dir / "templates" / "static" / "detections"

_detection_paths: list[Path] = list(_detection_template_dir.glob("*.js"))
_detection_files: list[dict[str, Any]] = []

try:
    for _detection_path in _detection_paths:
        with open(_detection_path, "r") as _detection_file:
            _detection_files.append(
                {
                    "file_name": _detection_path.name,
                    "content": _detection_file.read(),
                }
            )

except Exception:
    logger.exception(f"Failed to read detection files in detections folder!")


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
        for _miner_file_pm in val:
            _content_lines = _miner_file_pm.content.splitlines()
            if len(_content_lines) > 500:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file contains too many lines, should be <= 500 lines!"
                )

        return val


__all__ = [
    "MinerInput",
    "DetectionFilePM",
    "MinerOutput",
]
