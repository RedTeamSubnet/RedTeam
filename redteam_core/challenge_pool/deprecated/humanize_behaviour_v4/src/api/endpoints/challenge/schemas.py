# -*- coding: utf-8 -*-

import os
import pathlib
from typing import Optional, Union, List, Dict, Any

from pydantic import BaseModel, Field, constr, field_validator

from api.core.constants import (
    ALPHANUM_REGEX,
    ALPHANUM_HOST_REGEX,
    ALPHANUM_EXTEND_REGEX,
    REQUIREMENTS_REGEX,
    ALPHANUM_CUSTOM_REGEX,
)
from api.config import config
from api.core import utils


_src_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
_bot_core_dir = _src_dir / "bot" / "src" / "core"

_bot_py_path = str(_bot_core_dir / "bot.py")
_bot_py_content = "def run_bot(driver):\n    print('Hello, World!')"
if os.path.exists(_bot_py_path):
    with open(_bot_py_path, "r") as _bot_py_file:
        _bot_py_content = _bot_py_file.read()

_requirements_txt_path = str(_src_dir / "bot" / "requirements.txt")
_pip_requirements: Union[List[str], None] = None
if os.path.exists(_requirements_txt_path):
    with open(_requirements_txt_path, "r") as _requirements_txt_file:
        _pip_requirements = [_line.strip() for _line in _requirements_txt_file]


class KeyPairPM(BaseModel):
    private_key: str = Field(
        ...,
        min_length=32,
        title="Private Key",
        description="Private key as a string.",
    )
    public_key: Union[str, None] = Field(
        ...,
        min_length=32,
        title="Public Key",
        description="Public key as a string.",
    )
    nonce: Union[
        constr(
            strip_whitespace=True,
            min_length=4,
            max_length=64,
            pattern=ALPHANUM_REGEX,
        ),  # type: ignore
        None,
    ] = Field(
        ...,
        title="Nonce",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class MinerFilePM(BaseModel):
    fname: constr(strip_whitespace=True) = Field(  # type: ignore
        ...,
        min_length=4,
        max_length=64,
        pattern=ALPHANUM_HOST_REGEX,
        title="File Name",
        description="Name of the file.",
        examples=["config.py"],
    )
    content: constr(strip_whitespace=True) = Field(  # type: ignore
        ...,
        min_length=2,
        title="File Content",
        description="Content of the file as a string.",
        examples=["threshold = 0.5"],
    )

    @field_validator("fname")
    @classmethod
    def _check_fname(cls, val: str) -> str:

        if not isinstance(val, str):
            raise TypeError("File name must be a string!")

        if val.startswith("."):
            raise ValueError("File name cannot start with a dot(.)!")

        _allowed_exts = config.challenge.allowed_file_exts
        if not val.endswith(tuple(_allowed_exts)):
            raise ValueError(
                f"File extension is not supported, only '{_allowed_exts}' extensions are allowed!"
            )

        return val


class MinerInput(BaseModel):
    random_val: Optional[
        constr(
            strip_whitespace=True, min_length=4, max_length=64, pattern=ALPHANUM_REGEX
        )  # type: ignore
    ] = Field(
        default_factory=utils.gen_random_string,
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class MinerOutput(BaseModel):
    bot_py: str = Field(
        ...,
        title="bot.py",
        min_length=2,
        description="The main bot.py source code for the challenge.",
        examples=[_bot_py_content],
    )
    system_deps: Optional[
        constr(strip_whitespace=True, min_length=2, max_length=2048, pattern=ALPHANUM_EXTEND_REGEX)  # type: ignore
    ] = Field(
        default=None,
        title="System Dependencies",
        description="System dependencies (Debian/Ubuntu) that needs to be installed as space-separated string.",
        examples=[None, "python3 python3-pip"],
    )
    pip_requirements: Optional[
        List[constr(min_length=2, max_length=128, pattern=REQUIREMENTS_REGEX)]  # type: ignore
    ] = Field(
        default=None,
        title="Pip Requirements",
        description="Dependencies required for the bot.py as a list of strings.",
        examples=[_pip_requirements],
    )

    @field_validator("bot_py", mode="after")
    @classmethod
    def _check_bot_py_lines(cls, val: str) -> str:
        _lines = val.split("\n")
        if len(_lines) > 2000:
            raise ValueError("bot_py content is too long, max 2000 lines are allowed!")
        return val

    # extra_files: Optional[List[MinerFilePM]] = Field(
    #     default=None,
    #     title="Extra Files",
    #     description="List of extra files to support the bot.py.",
    #     examples=[
    #         [
    #             {
    #                 "fname": "config.py",
    #                 "content": "threshold = 0.5",
    #             }
    #         ]
    #     ],
    # )


class ErrorData(BaseModel):
    data: str = Field(
        ...,
        min_length=2,
        pattern=ALPHANUM_CUSTOM_REGEX,
        description="Bot data to evaluate.",
        examples=["data"],
    )


class EvalPayload(BaseModel):
    error: ErrorData


class RandomValRequest(BaseModel):
    random_val: str = Field(
        ...,
        min_length=4,
        max_length=64,
        pattern=ALPHANUM_REGEX,
        title="Random value",
        description="Random value.",
        examples=["a1b2c3d4e5f6g7h8"]
    )

__all__ = [
    "KeyPairPM",
    "MinerInput",
    "MinerOutput",
    "EvalPayload",
    "RandomValRequest"
]
