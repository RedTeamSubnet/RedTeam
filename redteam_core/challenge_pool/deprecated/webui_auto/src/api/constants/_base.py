# -*- coding: utf-8 -*-

from enum import Enum


ENV_PREFIX = "WUC_"
ENV_PREFIX_API = f"{ENV_PREFIX}API_"


class EnvEnum(str, Enum):
    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    DEMO = "DEMO"
    DOCS = "DOCS"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class WarnEnum(str, Enum):
    ERROR = "ERROR"
    ALWAYS = "ALWAYS"
    DEBUG = "DEBUG"
    IGNORE = "IGNORE"


class HashAlgoEnum(str, Enum):
    md5 = "md5"
    sha1 = "sha1"
    sha224 = "sha224"
    sha256 = "sha256"
    sha384 = "sha384"
    sha512 = "sha512"


__all__ = [
    "ENV_PREFIX",
    "ENV_PREFIX_API",
    "EnvEnum",
    "WarnEnum",
    "HashAlgoEnum",
]
