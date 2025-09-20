# -*- coding: utf-8 -*-

from typing import Optional, List

from pydantic import BaseModel, Field, constr


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
    random_val: Optional[
        constr(strip_whitespace=True, min_length=4, max_length=64)  # type: ignore
    ] = Field(
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class MinerOutput(BaseModel):
    fingerprinter_js: str = Field(
        ...,
        title="fingerprinter.js",
        min_length=2,
        description="The main fingerprinter.js source code for the challenge.",
        examples=[
            "function detectDriver() { localStorage.setItem('driver', 'Chrome'); }"
        ],
    )


__all__ = [
    "MinerInput",
    "MinerOutput",
]
