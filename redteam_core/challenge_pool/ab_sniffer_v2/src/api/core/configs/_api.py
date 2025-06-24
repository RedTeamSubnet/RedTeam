# -*- coding: utf-8 -*-

import sys
from typing import Any, Dict

from pydantic import Field, constr, field_validator, ValidationInfo, model_validator
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_API, HTTPSchemeEnum
from ._base import BaseConfig
from ._dev import DevConfig
from ._security import SecurityConfig
from ._docs import DocsConfig, FrozenDocsConfig
from ._paths import PathsConfig, FrozenPathsConfig


class ApiConfig(BaseConfig):
    name: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=128)  # type: ignore
    slug: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=128)  # type: ignore
    http_scheme: HTTPSchemeEnum = Field(default=HTTPSchemeEnum.http)
    bind_host: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=128)  # type: ignore
    port: int = Field(..., ge=80, lt=65536)
    version: constr(strip_whitespace=True) = Field(..., min_length=1, max_length=16)  # type: ignore
    prefix: constr(strip_whitespace=True) = Field(..., max_length=128)  # type: ignore
    gzip_min_size: int = Field(..., ge=0, le=10_485_760)  # 512 bytes
    behind_proxy: bool = Field(...)
    behind_cf_proxy: bool = Field(...)
    dev: DevConfig = Field(...)
    security: SecurityConfig = Field(...)
    docs: DocsConfig = Field(...)
    paths: PathsConfig = Field(...)

    @field_validator("slug")
    @classmethod
    def _check_slug(cls, val: str, info: ValidationInfo) -> str:
        if (not val) and ("name" in info.data):
            val = (
                info.data["name"]
                .lower()
                .strip()
                .replace(" ", "-")
                .replace("_", "-")
                .replace(".", "-")
            )

        return val

    @field_validator("prefix")
    @classmethod
    def _check_prefix(cls, val: str, info: ValidationInfo) -> str:
        if val and ("{api_version}" in val) and ("version" in info.data):
            val = val.format(api_version=info.data["version"])

        return val

    @field_validator("docs")
    @classmethod
    def _check_docs(cls, val: DocsConfig, info: ValidationInfo) -> DocsConfig:
        if val.enabled and ("prefix" in info.data):
            if val.openapi_url and ("{api_prefix}" in val.openapi_url):
                val.openapi_url = val.openapi_url.format(api_prefix=info.data["prefix"])

            if val.docs_url and ("{api_prefix}" in val.docs_url):
                val.docs_url = val.docs_url.format(api_prefix=info.data["prefix"])

            if val.redoc_url and ("{api_prefix}" in val.redoc_url):
                val.redoc_url = val.redoc_url.format(api_prefix=info.data["prefix"])

            if val.swagger_ui_oauth2_redirect_url and (
                "{api_prefix}" in val.swagger_ui_oauth2_redirect_url
            ):
                val.swagger_ui_oauth2_redirect_url = (
                    val.swagger_ui_oauth2_redirect_url.format(
                        api_prefix=info.data["prefix"]
                    )
                )

        val = FrozenDocsConfig(**val.model_dump())
        return val

    @field_validator("paths")
    @classmethod
    def _check_paths(cls, val: PathsConfig, info: ValidationInfo) -> FrozenPathsConfig:
        if "slug" in info.data:
            if "{api_slug}" in val.tmp_dir:
                val.tmp_dir = val.tmp_dir.format(api_slug=info.data["slug"])

            if "{api_slug}" in val.uploads_dir:
                val.uploads_dir = val.uploads_dir.format(api_slug=info.data["slug"])
            elif "{tmp_dir}" in val.uploads_dir:
                val.uploads_dir = val.uploads_dir.format(tmp_dir=val.tmp_dir)

            if "{api_slug}" in val.data_dir:
                val.data_dir = val.data_dir.format(api_slug=info.data["slug"])

        val = FrozenPathsConfig(**val.model_dump())
        return val

    @model_validator(mode="before")
    @classmethod
    def _check_args(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if (
            sys.argv[0].endswith("uvicorn")
            or sys.argv[0].endswith("fastapi")
            or sys.argv[0].endswith("gunicorn")
        ):
            _has_host = False
            for _i, _arg in enumerate(sys.argv):
                if _arg.startswith("--ssl"):
                    values["http_scheme"] = HTTPSchemeEnum.https

                if _arg.startswith("--host="):
                    _has_host = True
                    values["bind_host"] = _arg.split("=")[1]
                elif (_arg == "--host") and (_i + 1 < len(sys.argv)):
                    _has_host = True
                    values["bind_host"] = sys.argv[_i + 1]

                if _arg.startswith("--port="):
                    values["port"] = int(_arg.split("=")[1])
                elif (_arg == "--port") and (_i + 1 < len(sys.argv)):
                    values["port"] = int(sys.argv[_i + 1])

            if not _has_host:
                values["bind_host"] = "127.0.0.1"

                if sys.argv[0].endswith("fastapi") and sys.argv[1] == "run":
                    values["bind_host"] = "0.0.0.0"

        elif values["security"]["ssl"]["enabled"]:
            values["http_scheme"] = HTTPSchemeEnum.https

        return values

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_API)


class FrozenApiConfig(ApiConfig):
    model_config = SettingsConfigDict(frozen=True)


__all__ = ["ApiConfig", "FrozenApiConfig"]
