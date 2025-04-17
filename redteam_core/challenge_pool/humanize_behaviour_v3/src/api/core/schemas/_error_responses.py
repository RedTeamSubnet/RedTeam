# -*- coding: utf-8 -*-

from typing import Any, Union

from pydantic import Field

from ._responses import BaseResPM, ErrorResPM


class BadBaseResPM(BaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Bad Request!"],
    )
    data: Union[Any, dict, list] = Field(
        default=None,
        title="Data",
        description="Resource data or any response related data.",
        examples=[None],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "400_00000",
                "description": "Bad request syntax or unsupported method.",
                "detail": None,
            }
        ],
    )


class UnauthorizedBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Unauthorized!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "401_00000",
                "description": "No permission -- see authorization schemes.",
                "detail": None,
            }
        ],
    )


class ForbiddenBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Forbidden!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "403_00000",
                "description": "Request forbidden -- authorization will not help.",
                "detail": None,
            }
        ],
    )


class NotFoundBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Not Found!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "404_00000",
                "description": "Nothing matches the given URI.",
                "detail": "Not found any resource!",
            }
        ],
    )


class MethodNotBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Method Not Allowed!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "405_00000",
                "description": "Specified method is invalid for this resource.",
                "detail": None,
            }
        ],
    )


class ConflictBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Conflict!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "409_00000",
                "description": "Conflict occurred or current resource is already exists.",
                "detail": None,
            }
        ],
    )


class InvalidBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Validation error!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "422_00000",
                "description": "Error description.",
                "detail": [
                    {
                        "loc": ["body", "field"],
                        "msg": "Error message.",
                        "type": "Error type.",
                        "ctx": {"constraint": "value"},
                    }
                ],
            }
        ],
    )


class ErrorBaseResPM(BadBaseResPM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Internal Server Error!"],
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[
            {
                "code": "500_00000",
                "description": "Server got itself in trouble.",
                "detail": None,
            }
        ],
    )


__all__ = [
    "BadBaseResPM",
    "UnauthorizedBaseResPM",
    "ForbiddenBaseResPM",
    "NotFoundBaseResPM",
    "MethodNotBaseResPM",
    "ConflictBaseResPM",
    "InvalidBaseResPM",
    "ErrorBaseResPM",
]
