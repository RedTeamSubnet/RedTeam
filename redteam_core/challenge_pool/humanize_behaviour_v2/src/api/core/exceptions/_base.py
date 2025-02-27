# -*- coding: utf-8 -*-

from typing import Any, Optional, Dict

from pydantic import conint, constr, validate_call
from fastapi import HTTPException

from api.core.constants import ErrorCodeEnum


class BaseHTTPException(HTTPException):
    """Base HTTPException class for most of the http exceptions with custom error codes.

    Inherits:
        HTTPException: Exception class from FastAPI.
    """

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        error_enum: ErrorCodeEnum,
        status_code: Optional[conint(ge=100, le=599)] = None,  # type: ignore
        message: Optional[
            constr(strip_whitespace=True, min_length=1, max_length=256)  # type: ignore
        ] = None,
        description: Optional[constr(strip_whitespace=True, max_length=1024)] = None,  # type: ignore
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Constructor method for BaseHTTPException class.

        Args:
            error_enum  (ErrorCodeEnum           , required): Main error code enum.
            status_code (Optional[int]           , optional): HTTP status code: [ge=100, le=599]. Defaults to None.
            message     (Optional[str]           , optional): Error message: [min_length=1, max_length=255]. Defaults to None.
            description (Optional[str]           , optional): Error description: [max_length=511]. Defaults to None.
            detail      (Any                     , optional): Error detail. Defaults to None.
            headers     (Optional[Dict[str, str]], optional): Headers. Defaults to None.
        """

        _error = error_enum.value.model_dump()

        if not status_code:
            status_code: int = _error.get("status_code")

        if not message:
            message: str = _error.get("message")

        if description:
            _error["description"] = description

        if detail:
            _error["detail"] = detail

        super().__init__(
            status_code=status_code,
            detail={"message": message, "error": _error},
            headers=headers,
        )


class EmptyValueError(ValueError):
    """Class for catching required input empty errors.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class PrimaryKeyError(ValueError):
    """Class for catching primary key errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class UniqueKeyError(ValueError):
    """Class for catching unique constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class NullConstraintError(ValueError):
    """Class for catching null constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class ForeignKeyError(ValueError):
    """Class for catching foreign key constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


class CheckConstraintError(ValueError):
    """Class for catching check constraint errors from database.

    Inherits:
        ValueError: ValueError class from Python.
    """

    pass


__all__ = [
    "BaseHTTPException",
    "EmptyValueError",
    "PrimaryKeyError",
    "UniqueKeyError",
    "NullConstraintError",
    "ForeignKeyError",
    "CheckConstraintError",
]
