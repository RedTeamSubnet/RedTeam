# -*- coding: utf-8 -*-

from enum import Enum
from http import HTTPStatus
from typing import Union, Optional, Any

from pydantic import BaseModel, Field, constr


class ErrorCodePM(BaseModel):
    code: constr(strip_whitespace=True) = Field(..., min_length=3, max_length=36)  # type: ignore
    name: constr(strip_whitespace=True) = Field(..., min_length=3, max_length=64)  # type: ignore
    status_code: int = Field(..., ge=100, le=599)
    message: constr(strip_whitespace=True) = Field(..., min_length=1, max_length=256)  # type: ignore
    description: Optional[constr(strip_whitespace=True)] = Field(  # type: ignore
        default=None, max_length=1024
    )
    detail: Any = Field(default=None)


class ErrorCodeEnum(Enum):
    BAD_REQUEST = ErrorCodePM(
        code="400_00000",
        name="BAD_REQUEST",
        status_code=400,
        message=f"{HTTPStatus(400).phrase}!",
        description=f"{HTTPStatus(400).description}.",
        detail=None,
    )
    UNAUTHORIZED = ErrorCodePM(
        code="401_00000",
        name="UNAUTHORIZED",
        status_code=401,
        message=f"{HTTPStatus(401).phrase}!",
        description=f"{HTTPStatus(401).description}.",
        detail=None,
    )
    TOKEN_EXPIRED = ErrorCodePM(
        code="401_01000",
        name="TOKEN_EXPIRED",
        status_code=401,
        message="Token has expired!",
        description=f"{HTTPStatus(401).description}.",
        detail=None,
    )
    TOKEN_INVALID = ErrorCodePM(
        code="401_01001",
        name="TOKEN_INVALID",
        status_code=401,
        message="Token is invalid!",
        description=f"{HTTPStatus(401).description}.",
        detail=None,
    )
    FORBIDDEN = ErrorCodePM(
        code="403_00000",
        name="FORBIDDEN",
        status_code=403,
        message=f"{HTTPStatus(403).phrase}!",
        description=f"{HTTPStatus(403).description}.",
        detail=None,
    )
    NOT_VERIFIED = ErrorCodePM(
        code="403_00001",
        name="NOT_VERIFIED",
        status_code=403,
        message="Not verified!",
        description=f"{HTTPStatus(403).description}.",
        detail=None,
    )
    TOKEN_NOT_EXPIRED = ErrorCodePM(
        code="403_01000",
        name="TOKEN_NOT_EXPIRED",
        status_code=403,
        message="Token has not expired!",
        description=f"{HTTPStatus(403).description}.",
        detail=None,
    )
    NOT_FOUND = ErrorCodePM(
        code="404_00000",
        name="NOT_FOUND",
        status_code=404,
        message=f"{HTTPStatus(404).phrase}!",
        description=f"{HTTPStatus(404).description}.",
        detail=None,
    )
    METHOD_NOT_ALLOWED = ErrorCodePM(
        code="405_00000",
        name="METHOD_NOT_ALLOWED",
        status_code=405,
        message=f"{HTTPStatus(405).phrase}!",
        description=f"{HTTPStatus(405).description}.",
        detail=None,
    )
    NOT_ACCEPTABLE = ErrorCodePM(
        code="406_00000",
        name="NOT_ACCEPTABLE",
        status_code=406,
        message=f"{HTTPStatus(406).phrase}!",
        description=f"{HTTPStatus(406).description}.",
        detail=None,
    )
    REQUEST_TIMEOUT = ErrorCodePM(
        code="408_00000",
        name="REQUEST_TIMEOUT",
        status_code=408,
        message=f"{HTTPStatus(408).phrase}!",
        description=f"{HTTPStatus(408).description}.",
        detail=None,
    )
    CONFLICT = ErrorCodePM(
        code="409_00000",
        name="CONFLICT",
        status_code=409,
        message=f"{HTTPStatus(409).phrase}!",
        description=f"{HTTPStatus(409).description}.",
        detail=None,
    )
    REQUEST_ENTITY_TOO_LARGE = ErrorCodePM(
        code="413_00000",
        name="REQUEST_ENTITY_TOO_LARGE",
        status_code=413,
        message=f"{HTTPStatus(413).phrase}!",
        description=f"{HTTPStatus(413).description}.",
        detail=None,
    )
    REQUEST_URI_TOO_LONG = ErrorCodePM(
        code="414_00000",
        name="REQUEST_URI_TOO_LONG",
        status_code=414,
        message=f"{HTTPStatus(414).phrase}!",
        description=f"{HTTPStatus(414).description}.",
        detail=None,
    )
    UNSUPPORTED_MEDIA_TYPE = ErrorCodePM(
        code="415_00000",
        name="UNSUPPORTED_MEDIA_TYPE",
        status_code=415,
        message=f"{HTTPStatus(415).phrase}!",
        description=f"{HTTPStatus(415).description}.",
        detail=None,
    )
    UNPROCESSABLE_ENTITY = ErrorCodePM(
        code="422_00000",
        name="UNPROCESSABLE_ENTITY",
        status_code=422,
        message=f"{HTTPStatus(422).phrase}!",
        description=None,
        detail=None,
    )
    LOCKED = ErrorCodePM(
        code="423_00000",
        name="LOCKED",
        status_code=423,
        message=f"{HTTPStatus(423).phrase}!",
        description=f"{HTTPStatus(423).description}.",
        detail=None,
    )
    TOO_MANY_REQUESTS = ErrorCodePM(
        code="429_00000",
        name="TOO_MANY_REQUESTS",
        status_code=429,
        message=f"{HTTPStatus(429).phrase}!",
        description=f"{HTTPStatus(429).description}.",
        detail=None,
    )
    INTERNAL_SERVER_ERROR = ErrorCodePM(
        code="500_00000",
        name="INTERNAL_SERVER_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
        detail=None,
    )
    DB_ERROR = ErrorCodePM(
        code="500_10000",
        name="DB_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
        detail=None,
    )
    DB_PK_ERROR = ErrorCodePM(
        code="500_10001",
        name="DB_PK_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
        detail=None,
    )
    DB_UQ_ERROR = ErrorCodePM(
        code="500_10002",
        name="DB_UQ_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
        detail=None,
    )
    SMTP_ERROR = ErrorCodePM(
        code="500_20000",
        name="SMTP_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
        detail=None,
    )
    SERVICE_UNAVAILABLE = ErrorCodePM(
        code="503_00000",
        name="SERVICE_UNAVAILABLE",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
        detail=None,
    )
    DB_CONNECT_ERROR = ErrorCodePM(
        code="503_10000",
        name="DB_CONNECT_ERROR",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
        detail=None,
    )
    SMTP_CONNECT_ERROR = ErrorCodePM(
        code="503_20000",
        name="SMTP_CONNECT_ERROR",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
        detail=None,
    )

    @classmethod
    def get_by_code(
        cls,
        code: str,
    ) -> Union["ErrorCodeEnum", None]:
        for _error_code_enum in ErrorCodeEnum:
            if _error_code_enum.value.code == code:
                return _error_code_enum
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Union["ErrorCodeEnum", None]:
        for _error_code_enum in ErrorCodeEnum:
            if _error_code_enum.value.name == name:
                return _error_code_enum
        return None

    @classmethod
    def get_by_status_code(cls, status_code: int) -> Union["ErrorCodeEnum", None]:
        for _error_code_enum in ErrorCodeEnum:
            if _error_code_enum.value.status_code == status_code:
                return _error_code_enum
        return None


__all__ = ["ErrorCodePM", "ErrorCodeEnum"]
