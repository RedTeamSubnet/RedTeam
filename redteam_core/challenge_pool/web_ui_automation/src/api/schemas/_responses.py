# -*- coding: utf-8 -*-

from enum import Enum
from typing import Any, Union, Optional

from pydantic import Field, constr

from api.config import config
from ._base import ExtraBasePM, BasePM


class MethodEnum(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    CONNECT = "CONNECT"
    TRACE = "TRACE"


class LinksResPM(ExtraBasePM):
    self_link: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        alias="self",
        title="Self link",
        description="Link to the current resource.",
        examples=[f"{config.api.prefix}/resources"],
    )


class PageLinksResPM(LinksResPM):
    first_link: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        alias="first",
        title="First link",
        description="Link to the first page of the resource.",
        examples=[f"{config.api.prefix}/resources/?skip=0&limit=100"],
    )
    prev_link: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        alias="prev",
        title="Previous link",
        description="Link to the previous page of the resource.",
        examples=[f"{config.api.prefix}/resources/?skip=100&limit=100"],
    )
    next_link: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        alias="next",
        title="Next link",
        description="Link to the next page of the resource.",
        examples=[f"{config.api.prefix}/resources/?skip=300&limit=100"],
    )
    last_link: Optional[constr(strip_whitespace=True, max_length=2048)] = Field(  # type: ignore
        default=None,
        alias="last",
        title="Last link",
        description="Link to the last page of the resource.",
        examples=[f"{config.api.prefix}/resources/?skip=400&limit=100"],
    )


class MetaResPM(ExtraBasePM):
    request_id: Optional[
        constr(strip_whitespace=True, min_length=8, max_length=64)  # type: ignore
    ] = Field(
        default=None,
        title="Request ID",
        description="Current request ID.",
        examples=["211203afa2844d55b1c9d38b9f8a7063"],
    )
    base_url: Optional[
        constr(strip_whitespace=True, min_length=2, max_length=256)  # type: ignore
    ] = Field(
        default=None,
        title="Base URL",
        description="Current request base URL.",
        examples=["https://api.example.com"],
    )
    method: Optional[MethodEnum] = Field(
        default=None,
        title="Method",
        description="Current request method.",
        examples=["GET"],
    )
    api_version: constr(strip_whitespace=True) = Field(  # type: ignore
        default=config.api.version,
        min_length=1,
        max_length=16,
        title="API version",
        description="Current API version.",
        examples=[config.api.version],
    )
    version: constr(strip_whitespace=True) = Field(  # type: ignore
        default=config.version,
        min_length=5,
        max_length=32,
        title="Version",
        description="Current system version.",
        examples=[config.version],
    )


class ErrorResPM(BasePM):
    code: constr(strip_whitespace=True) = Field(  # type: ignore
        ...,
        min_length=3,
        max_length=36,
        title="Error code",
        description="Code that represents the error.",
        examples=["400_00000"],
    )
    description: Optional[constr(strip_whitespace=True)] = Field(  # type: ignore
        default=None,
        max_length=1024,
        title="Error description",
        description="Description of the error.",
        examples=["Bad request syntax or unsupported method."],
    )
    detail: Union[Any, dict, list] = Field(
        default=None,
        title="Error detail",
        description="Detail of the error.",
        examples=[
            {
                "loc": ["body", "field"],
                "msg": "Error message.",
                "type": "Error type.",
                "ctx": {"constraint": "value"},
            }
        ],
    )


class BaseResPM(BasePM):
    message: str = Field(
        ...,
        min_length=1,
        max_length=256,
        title="Message",
        description="Response message about the current request.",
        examples=["Successfully processed the request."],
    )
    data: Union[Any, dict, list] = Field(
        default=None,
        title="Data",
        description="Resource data or any data related to response.",
        examples=["Any data: dict, list, str, int, float, null, etc."],
    )
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current request or resource.",
    )
    meta: MetaResPM = Field(
        default_factory=MetaResPM,
        title="Meta",
        description="Meta information about the current request.",
    )
    error: Union[ErrorResPM, Any] = Field(
        default=None,
        title="Error",
        description="Error information about the current request.",
        examples=[None],
    )


__all__ = [
    "LinksResPM",
    "PageLinksResPM",
    "MetaResPM",
    "ErrorResPM",
    "BaseResPM",
]
