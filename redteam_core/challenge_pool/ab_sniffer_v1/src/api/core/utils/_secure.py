# -*- coding: utf-8 -*-

import uuid
import string
import secrets
import hashlib

from pydantic import validate_call, conint, constr

from api.core.constants import HashAlgoEnum
from ._dt import now_ts


@validate_call
def gen_unique_id(prefix: constr(strip_whitespace=True, max_length=32) = "") -> str:  # type: ignore
    """Generate unique id.

    Args:
        prefix (str, optional): Prefix of id. Defaults to ''.

    Returns:
        str: Unique id.
    """

    _id = str(f"{prefix}{now_ts()}_{uuid.uuid4().hex}").lower()
    return _id


@validate_call
def gen_random_string(length: conint(ge=1) = 16, is_alphanum: bool = True) -> str:  # type: ignore
    """Generate secure random string.

    Args:
        length      (int , optional): Length of random string. Defaults to 16.
        is_alphanum (bool, optional): If True, generate only alphanumeric string. Defaults to True.

    Returns:
        str: Generated random string.
    """

    _base_chars = string.ascii_letters + string.digits
    if not is_alphanum:
        _base_chars += string.punctuation

    _random_str = "".join(secrets.choice(_base_chars) for _i in range(length))
    return _random_str


@validate_call
def hash_str(val: str, algorithm: HashAlgoEnum = HashAlgoEnum.sha256) -> str:
    """Hash a string using a specified hash algorithm.

    Args:
        val       (str         , required): The string to hash.
        algorithm (HashAlgoEnum, required): The hash algorithm to use. Defaults to `HashAlgoEnum.sha256`.

    Returns:
        str: The hexadecimal representation of the digest.
    """

    if not isinstance(val, bytes):
        val = val.encode("utf-8")

    _hash = hashlib.new(algorithm.value)
    _hash.update(val)

    _hash_val = _hash.hexdigest()
    return _hash_val


__all__ = [
    "gen_unique_id",
    "gen_random_string",
    "hash_str",
]
