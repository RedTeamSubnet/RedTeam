# -*- coding: utf-8 -*-

from typing import List, Optional

from pydantic import Field, constr
from pydantic_settings import SettingsConfigDict

from api.core.constants import (
    ENV_PREFIX_API,
    HTTP_METHOD_REGEX,
    ASYMMETRIC_ALGORITHM_REGEX,
)
from ._base import FrozenBaseConfig


_ENV_PREFIX_SECURITY = f"{ENV_PREFIX_API}SECURITY_"


class CorsConfig(FrozenBaseConfig):
    allow_origins: List[
        constr(strip_whitespace=True, min_length=1, max_length=256)  # type: ignore
    ] = Field(...)
    allow_origin_regex: Optional[
        constr(strip_whitespace=True, min_length=1, max_length=256)  # type: ignore
    ] = Field(default=None)
    allow_headers: List[
        constr(strip_whitespace=True, min_length=1, max_length=128)  # type: ignore
    ] = Field(...)
    allow_methods: List[constr(strip_whitespace=True, pattern=HTTP_METHOD_REGEX)] = (  # type: ignore
        Field(...)
    )
    allow_credentials: bool = Field(...)
    expose_headers: List[
        constr(strip_whitespace=True, min_length=1, max_length=128)  # type: ignore
    ] = Field(...)
    max_age: int = Field(..., ge=0, le=86_400)

    model_config = SettingsConfigDict(env_prefix=f"{_ENV_PREFIX_SECURITY}CORS_")


class X509AttrsConfig(FrozenBaseConfig):
    C: constr(strip_whitespace=True, to_upper=True) = Field(default="US", min_length=2, max_length=2)  # type: ignore
    ST: constr(strip_whitespace=True) = Field(default="Washington", min_length=2, max_length=256)  # type: ignore
    L: constr(strip_whitespace=True) = Field(default="Seattle", min_length=2, max_length=256)  # type: ignore
    O: constr(strip_whitespace=True) = Field(default="Organization", min_length=2, max_length=256)  # type: ignore
    OU: constr(strip_whitespace=True) = Field(default="Organization Unit", min_length=2, max_length=256)  # type: ignore
    CN: constr(strip_whitespace=True) = Field(default="localhost", min_length=2, max_length=256)  # type: ignore
    DNS: constr(strip_whitespace=True) = Field(default="localhost", min_length=2, max_length=256)  # type: ignore

    model_config = SettingsConfigDict(
        env_prefix=f"{_ENV_PREFIX_SECURITY}SSL_X509_ATTRS_"
    )


class SSLConfig(FrozenBaseConfig):
    enabled: bool = Field(...)
    generate: bool = Field(...)
    key_size: int = Field(..., ge=2048, le=8192)
    key_fname: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=256)  # type: ignore
    cert_fname: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=256)  # type: ignore
    x509_attrs: X509AttrsConfig = Field(default_factory=X509AttrsConfig)

    model_config = SettingsConfigDict(env_prefix=f"{_ENV_PREFIX_SECURITY}SSL_")


class AsymmetricConfig(FrozenBaseConfig):
    generate: bool = Field(...)
    algorithm: constr(strip_whitespace=True) = Field(..., pattern=ASYMMETRIC_ALGORITHM_REGEX)  # type: ignore
    key_size: int = Field(..., ge=2048, le=8192)
    private_key_fname: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=256
    )
    public_key_fname: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=256
    )

    model_config = SettingsConfigDict(env_prefix=f"{_ENV_PREFIX_SECURITY}ASYMMETRIC_")


class SecurityConfig(FrozenBaseConfig):
    allowed_hosts: List[constr(strip_whitespace=True, min_length=1, max_length=256)] = (  # type: ignore
        Field(...)
    )
    forwarded_allow_ips: List[
        constr(strip_whitespace=True, min_length=1, max_length=256)  # type: ignore
    ] = Field(...)
    cors: CorsConfig = Field(...)
    ssl: SSLConfig = Field(...)
    asymmetric: AsymmetricConfig = Field(...)

    model_config = SettingsConfigDict(env_prefix=_ENV_PREFIX_SECURITY)


__all__ = [
    "SecurityConfig",
    "CorsConfig",
    "X509AttrsConfig",
    "SSLConfig",
    "AsymmetricConfig",
]
