# -*- coding: utf-8 -*-

import os
from typing import Any, Dict

from pydantic import Field, constr, model_validator, field_validator
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_API
from ._base import BaseConfig


class PathsConfig(BaseConfig):
    tmp_dir: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=1024)  # type: ignore
    uploads_dir: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=1024
    )
    data_dir: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=1024
    )
    security_dir: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=1024
    )
    ssl_dir: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=1024)  # type: ignore
    asymmetric_keys_dir: constr(strip_whitespace=True) = Field(  # type: ignore
        ..., min_length=2, max_length=1024
    )
    # models_dir: constr(strip_whitespace=True) = Field(  # type: ignore
    #     ..., min_length=2, max_length=1024
    # )
    # model_dir: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=1024)  # type: ignore

    @field_validator("data_dir")
    @classmethod
    def _check_data_dir(cls, val: str) -> str:
        _data_dir_env = f"{ENV_PREFIX_API}DATA_DIR"
        if _data_dir_env in os.environ:
            val = os.getenv(_data_dir_env)

        return val

    @field_validator("tmp_dir")
    @classmethod
    def _check_tmp_dir(cls, val: str) -> str:
        _tmp_dir_env = f"{ENV_PREFIX_API}TMP_DIR"
        if _tmp_dir_env in os.environ:
            val = os.getenv(_tmp_dir_env)

        return val

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX_API}PATHS_")


class FrozenPathsConfig(PathsConfig):
    @model_validator(mode="before")
    @classmethod
    def _check_all(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        for _key, _val in values.items():
            if isinstance(_val, str) and ("{data_dir}" in _val):
                values[_key] = _val.format(data_dir=values["data_dir"])

        return values

    model_config = SettingsConfigDict(frozen=True)


__all__ = ["PathsConfig", "FrozenPathsConfig"]
