# -*- coding: utf-8 -*-

import os
import pathlib
from typing import Optional, Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic.types import StringConstraints

from api.core.constants import ALPHANUM_REGEX
from api.core import utils


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_detection_template_dir = _src_dir / "templates" / "static" / "detections"

# Read detection.js
_detection_js_files = _detection_template_dir.glob("*.js")
_detection_files = {}
try:
    for js_file in _detection_js_files:
        with open(js_file, "r") as file:
            _detection_files[js_file.name] = file.read()
except Exception as e:
    print(f"Error: Failed to read detection files in detections folder: {e}")


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


class MinerOutput(BaseModel):
    detection_files: dict = Field(
        ...,
        title="js files",
        description="The main detection.js source code for the challenge.",
        examples=[_detection_files],
    )

    @field_validator("detection_files", mode="after")
    @classmethod
    def _check_detection_js_lines(cls, val: dict) -> dict:
        if not isinstance(val, dict):
            raise TypeError("detection_files must be a dict")
        for detection_name, detection_file in val.items():
            if not isinstance(detection_file, str):
                raise TypeError(f"detection file for {detection_name} must be a string")
            _lines = detection_file.splitlines()
            if len(_lines) > 500:
                raise ValueError(
                    f"script for detecting {detection_name} exceeds 500 line limit"
                )
        return val


__all__ = [
    "MinerInput",
    "MinerOutput",
]
