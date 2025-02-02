# -*- coding: utf-8 -*-

from typing import List, Optional, Union

from pydantic import BaseModel, Field, constr, field_validator, HttpUrl

from api.core.constants import (
    ALPHANUM_REGEX,
    ALPHANUM_HOST_REGEX,
    ALPHANUM_HYPHEN_REGEX,
)
from api.config import config
from api.core import utils


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
        examples=["config.py", "utils.py"],
    )
    content: constr(strip_whitespace=True) = Field(  # type: ignore
        ...,
        min_length=2,
        title="File Content",
        description="Content of the file as a string.",
        examples=["print('Hello, World!')"],
    )

    @field_validator("fname")
    @classmethod
    def _check_fname(cls, val: str) -> str:

        if not isinstance(val, str):
            raise TypeError("File name must be a string!")

        if val.startswith("."):
            raise ValueError("File name cannot start with a dot(.)!")

        _allowed_exts = config.api.security.allowed_miner_exts
        if not val.endswith(tuple(_allowed_exts)):
            raise ValueError(
                f"File extension is not supported, only '{_allowed_exts}' extensions are allowed!"
            )

        return val


class MinerInput(BaseModel):
    web_url: HttpUrl = Field(
        default="https://webui_auto:10001/web",
        title="Web URL",
        description="Webpage URL for the challenge.",
        examples=["https://webui_auto:10001/web"],
    )
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
    bot_py: constr(strip_whitespace=True, min_length=2) = Field(  # type: ignore
        ...,
        title="bot.py",
        description="The main bot.py source code for the challenge.",
        examples=["def run_bot(driver):\n    print('Hello, World!')"],
    )
    system_deps: Optional[
        List[
            constr(
                strip_whitespace=True,
                pattern=ALPHANUM_HYPHEN_REGEX,
                min_length=2,
                max_length=64,
            )  # type: ignore
        ]
    ] = Field(
        default=None,
        max_length=32,
        title="System Dependencies",
        description="List of system dependencies (Debian/Ubuntu) that needs to be installed.",
        examples=[["python3", "python3-pip", "iproute2"]],
    )
    requirements_txt: Optional[
        constr(strip_whitespace=True, min_length=2, max_length=2048)  # type: ignore
    ] = Field(
        default=None,
        title="requirements.txt",
        description="Dependencies required for the bot.py as a string (requirements.txt).",
        examples=["pydantic[email,timezone]>=2.0.0,<3.0.0\nselenium>=4.16.0,<5.0.0\n"],
    )
    extra_files: Optional[List[MinerFilePM]] = Field(
        default=None,
        title="Extra Files",
        description="List of extra files to support the bot.py.",
        examples=[
            [
                {
                    "fname": "config.py",
                    "content": "threshold = 0.5",
                }
            ]
        ],
    )


__all__ = [
    "KeyPairPM",
    "MinerInput",
    "MinerOutput",
]
