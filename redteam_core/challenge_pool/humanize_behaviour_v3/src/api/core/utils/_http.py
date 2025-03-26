# -*- coding: utf-8 -*-

from typing import Tuple, Union
from urllib import request
from http import HTTPStatus
from http.client import HTTPResponse

import aiohttp
from pydantic import validate_call, conint, AnyHttpUrl
from starlette.datastructures import URL
from fastapi import Request


@validate_call
def get_http_status(status_code: int) -> Tuple[HTTPStatus, bool]:
    """Get HTTP status code enum from integer value.

    Args:
        status_code (int, required): Status code for HTTP response: [100 <= status_code <= 599].

    Raises:
        ValueError: If status code is not in range [100 <= status_code <= 599].

    Returns:
        Tuple[HTTPStatus, bool]: Tuple of HTTP status code enum and boolean value if status code is known.
    """

    _http_status: HTTPStatus
    _is_known_status = False
    try:
        _http_status = HTTPStatus(status_code)
        _is_known_status = True
    except ValueError:
        if (100 <= status_code) and (status_code < 200):
            status_code = 100
        elif (200 <= status_code) and (status_code < 300):
            status_code = 200
        elif (300 <= status_code) and (status_code < 400):
            status_code = 304
        elif (400 <= status_code) and (status_code < 500):
            status_code = 400
        elif (500 <= status_code) and (status_code < 600):
            status_code = 500
        else:
            raise ValueError(f"Invalid HTTP status code: '{status_code}'!")

        _http_status = HTTPStatus(status_code)

    return (_http_status, _is_known_status)


@validate_call(config={"arbitrary_types_allowed": True})
def get_relative_url(val: Union[Request, URL]) -> str:
    """Get relative url only path with query params from request object or URL object.

    Args:
        val (Union[Request, URL]): Request object or URL object to extract relative url.

    Returns:
        str: Relative url only path with query params.
    """

    if isinstance(val, Request):
        val: URL = val.url

    _relative_url = str(val).replace(f"{val.scheme}://{val.netloc}", "")
    return _relative_url


@validate_call
async def async_is_connectable(
    url: AnyHttpUrl = "https://www.google.com",
    timeout: conint(ge=1) = 3,  # type: ignore
    check_status: bool = False,
) -> bool:
    """Check if the url is connectable.

    Args:
        url          (AnyHttpUrl, optional): URL to check. Defaults to 'https://www.google.com'.
        timeout      (int       , optional): Timeout in seconds. Defaults to 3.
        check_status (bool      , optional): Check HTTP status code (200). Defaults to False.

    Returns:
        bool: True if connectable, False otherwise.
    """

    try:
        async with aiohttp.ClientSession() as _session:
            async with _session.get(url, timeout=timeout) as _response:
                if check_status:
                    return _response.status == 200
                return True
    except:
        return False


@validate_call
def is_connectable(
    url: AnyHttpUrl = "https://www.google.com",
    timeout: conint(ge=1) = 3,  # type: ignore
    check_status: bool = False,
) -> bool:
    """Check if the url is connectable.

    Args:
        url          (AnyHttpUrl, optional): URL to check. Defaults to 'https://www.google.com'.
        timeout      (int       , optional): Timeout in seconds. Defaults to 3.
        check_status (bool      , optional): Check HTTP status code (200). Defaults to False.

    Returns:
        bool: True if connectable, False otherwise.
    """

    try:
        _response: HTTPResponse = request.urlopen(url, timeout=timeout)
        if check_status:
            return _response.getcode() == 200
        return True
    except:
        return False


__all__ = [
    "get_http_status",
    "get_relative_url",
    "async_is_connectable",
    "is_connectable",
]
