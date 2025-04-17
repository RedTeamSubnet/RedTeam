# -*- coding: utf-8 -*-

import re
from typing import List, Union, Pattern

from pydantic import validate_call

from api.core.constants import (
    REQUEST_ID_REGEX,
    SPECIAL_CHARS_BASE_REGEX,
    SPECIAL_CHARS_LOW_REGEX,
    SPECIAL_CHARS_MEDIUM_REGEX,
    SPECIAL_CHARS_HIGH_REGEX,
    SPECIAL_CHARS_STRICT_REGEX,
)


@validate_call
def is_truthy(val: Union[str, bool, int, float, None]) -> bool:
    """Check if the value is truthy.

    Args:
        val (Union[str, bool, int, float, None], required): Value to check.

    Raises:
        ValueError: If `val` argument type is string and value is invalid.

    Returns:
        bool: True if the value is truthy, False otherwise.
    """

    if isinstance(val, str):
        val = val.strip().lower()

        if val in ["0", "false", "f", "no", "n", "off"]:
            return False
        elif val in ["1", "true", "t", "yes", "y", "on"]:
            return True
        else:
            raise ValueError(f"`val` argument value is invalid: '{val}'!")

    return bool(val)


@validate_call
def is_falsy(val: Union[str, bool, int, float, None]) -> bool:
    """Check if the value is falsy.

    Args:
        val (Union[str, bool, int, float, None], required): Value to check.

    Returns:
        bool: True if the value is falsy, False otherwise.
    """

    return not is_truthy(val)


@validate_call
def is_request_id(val: str) -> bool:
    """Check if the string is valid request ID.

    Args:
        val (str, required): String to check.

    Returns:
        bool: True if the string is valid request ID, False otherwise.
    """

    _is_valid = bool(re.match(pattern=REQUEST_ID_REGEX, string=val))
    return _is_valid


@validate_call
def is_blacklisted(val: str, blacklist: List[str]) -> bool:
    """Check if the string is blacklisted.

    Args:
        val       (str      , required): String to check.
        blacklist (List[str], required): List of blacklisted strings.

    Returns:
        bool: True if the string is blacklisted, False otherwise.
    """

    for _blacklisted in blacklist:
        if _blacklisted in val:
            return True

    return False


@validate_call
def is_valid(val: str, pattern: Union[Pattern, str]) -> bool:
    """Check if the string is valid with given pattern.

    Args:
        val     (str                , required): String to check.
        pattern (Union[Pattern, str], required): Pattern regex to check.

    Returns:
        bool: True if the string is valid with given pattern, False otherwise.
    """

    _is_valid = bool(re.match(pattern=pattern, string=val))
    return _is_valid


@validate_call
def has_special_chars(val: str, mode: str = "LOW") -> bool:
    """Check if the string has special characters.

    Args:
        val  (str, required): String to check.
        mode (str, optional): Check mode. Defaults to "LOW".

    Raises:
        ValueError: If `mode` is unsupported.

    Returns:
        bool: True if the string has special characters, False otherwise.
    """

    _has_special_chars = False

    _pattern = r""
    mode = mode.upper()
    if (mode == "BASE") or (mode == "HTML"):
        _pattern = SPECIAL_CHARS_BASE_REGEX
    elif mode == "LOW":
        _pattern = SPECIAL_CHARS_LOW_REGEX
    elif mode == "MEDIUM":
        _pattern = SPECIAL_CHARS_MEDIUM_REGEX
    elif (mode == "HIGH") or (mode == "SCRIPT") or (mode == "SQL"):
        _pattern = SPECIAL_CHARS_HIGH_REGEX
    elif mode == "STRICT":
        _pattern = SPECIAL_CHARS_STRICT_REGEX
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    _has_special_chars = bool(re.search(pattern=_pattern, string=val))
    return _has_special_chars


__all__ = [
    "is_truthy",
    "is_falsy",
    "is_request_id",
    "is_blacklisted",
    "is_valid",
    "has_special_chars",
]
