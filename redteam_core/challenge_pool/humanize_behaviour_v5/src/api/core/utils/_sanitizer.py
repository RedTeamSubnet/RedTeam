# -*- coding: utf-8 -*-

import re
import html
from urllib.parse import quote

from pydantic import validate_call, constr, AnyHttpUrl

from api.core.constants import (
    SPECIAL_CHARS_BASE_REGEX,
    SPECIAL_CHARS_LOW_REGEX,
    SPECIAL_CHARS_MEDIUM_REGEX,
    SPECIAL_CHARS_HIGH_REGEX,
    SPECIAL_CHARS_STRICT_REGEX,
)


@validate_call
def escape_html(val: constr(strip_whitespace=True)) -> str:  # type: ignore
    """Escape HTML characters.

    Args:
        val (str, required): String to escape.

    Returns:
        str: Escaped string.
    """

    _escaped = html.escape(val)
    return _escaped


@validate_call
def espace_url(val: AnyHttpUrl) -> str:
    """Escape URL characters.

    Args:
        val (AnyHttpUrl, required): String to escape.

    Returns:
        str: Escaped string.
    """

    _escaped = quote(val)
    return _escaped


@validate_call
def clean_special_chars(val: str, mode: str = "LOW") -> str:
    """Sanitize special characters.

    Args:
        val  (str, required): String to sanitize.
        mode (str, optional): Sanitization mode. Defaults to "LOW".

    Raises:
        ValueError: If `mode` is unsupported.

    Returns:
        str: Sanitized string.
    """

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

    _sanitized = re.sub(pattern=_pattern, repl="", string=val)
    return _sanitized


__all__ = [
    "escape_html",
    "espace_url",
    "clean_special_chars",
]
