# -*- coding: utf-8 -*-

import os
import pathlib
from typing import Optional, Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic.types import StringConstraints

from api.core.constants import ALPHANUM_REGEX
from api.core import utils


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_detection_template_dir = _src_dir / "templates" / "static" / "detection"

# Read detection.js
_detection_js_path = str(_detection_template_dir / "detection.js")
_detection_js_content = "(function(){const driverType=getDriverType();localStorage.setItem('driver',driverType);})();"
try:
    if os.path.exists(_detection_js_path):
        with open(_detection_js_path, "r") as _detection_js_file:
            _detection_js_content = _detection_js_file.read()
except Exception as e:
    print(f"Error: Failed to read detection.js: {e}")


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
    detection_js: str = Field(
        default=_detection_js_content,
        title="detection.js",
        min_length=2,
        description="System-provided detection.js script for driver detection.",
        examples=[_detection_js_content],
    )

    @field_validator("detection_js", mode="after")
    @classmethod
    def _check_detection_js_lines(cls, val: str) -> str:
        _lines = val.split("\n")
        if len(_lines) > 1000:
            raise ValueError(
                "detection_js content is too long, max 1000 lines are allowed!"
            )
        return val


__all__ = [
    "MinerInput",
    "MinerOutput",
]
