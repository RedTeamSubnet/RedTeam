# -*- coding: utf-8 -*-

from enum import Enum


ENV_PREFIX = "ABSC_"
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


class LanguageEnum(str, Enum):
    en = "en"
    ko = "ko"
    mn = "mn"


class CurrencyEnum(str, Enum):
    USD = "USD"
    KRW = "KRW"
    MNT = "MNT"


class HashAlgoEnum(str, Enum):
    md5 = "md5"
    sha1 = "sha1"
    sha224 = "sha224"
    sha256 = "sha256"
    sha384 = "sha384"
    sha512 = "sha512"


class HTTPSchemeEnum(str, Enum):
    http = "http"
    https = "https"


__all__ = [
    "ENV_PREFIX",
    "ENV_PREFIX_API",
    "EnvEnum",
    "WarnEnum",
    "LanguageEnum",
    "CurrencyEnum",
    "HashAlgoEnum",
    "HTTPSchemeEnum",
]
