# -*- coding: utf-8 -*-

from typing import Optional, List

from pydantic import BaseModel, Field, constr, HttpUrl


class MinerFilePM(BaseModel):
    fname: constr(strip_whitespace=True) = Field(  # type: ignore
        ...,
        min_length=4,
        max_length=64,
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


class MinerInput(BaseModel):
    web_url: HttpUrl = Field(
        default="https://172.17.0.1:10001/web",
        title="Web URL",
        description="Webpage URL for the challenge.",
        examples=["https://172.17.0.1:10001/web"],
    )
    random_val: Optional[
        constr(strip_whitespace=True, min_length=4, max_length=64)  # type: ignore
    ] = Field(
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
        examples=["def run_bot(driver):\n    print('Hello, World!')"],
    )
    system_deps: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        title="System Dependencies",
        description="System dependencies (Debian/Ubuntu) that needs to be installed as space-separated string.",
        examples=["python3 python3-pip"],
    )
    requirements_txt: Optional[constr(max_length=2048)] = Field(  # type: ignore
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
    "MinerInput",
    "MinerOutput",
]
