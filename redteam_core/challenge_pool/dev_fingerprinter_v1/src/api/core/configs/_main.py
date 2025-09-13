# -*- coding: utf-8 -*-

import os
import json
import logging
from typing_extensions import Self

from pydantic import Field, constr, field_validator, ValidationInfo, model_validator
from pydantic_settings import SettingsConfigDict

from beans_logging import LoggerConfigPM

from api.__version__ import __version__
from api.core.constants import EnvEnum, ENV_PREFIX, ENV_PREFIX_API
from ._base import FrozenBaseConfig
from ._dev import DevConfig, FrozenDevConfig
from ._api import ApiConfig, FrozenApiConfig
from .challenge import ChallengeConfig


logger = logging.getLogger(__name__)


# Main config schema:
class MainConfig(FrozenBaseConfig):
    env: EnvEnum = Field(...)
    debug: bool = Field(...)
    version: constr(strip_whitespace=True) = Field(  # type: ignore
        default=__version__, min_length=3, max_length=32
    )
    api: ApiConfig = Field(...)
    challenge: ChallengeConfig = Field(...)
    logger: LoggerConfigPM = Field(default_factory=LoggerConfigPM)

    @field_validator("env")
    @classmethod
    def _check_env(cls, val: EnvEnum) -> EnvEnum:
        _env = "ENV"
        if _env in os.environ:
            _env = os.getenv(_env).upper()
            val = EnvEnum(_env)

        return val

    @field_validator("debug")
    @classmethod
    def _check_debug(cls, val: str) -> str:
        _debug_env = "DEBUG"
        if _debug_env in os.environ:
            val = os.getenv(_debug_env)

        return val

    @field_validator("version")
    @classmethod
    def _check_version(cls, val: str) -> str:
        val = __version__
        return val

    @field_validator("api")
    @classmethod
    def _check_api(cls, val: ApiConfig, info: ValidationInfo) -> FrozenApiConfig:
        _dev: DevConfig = val.dev
        if ("env" in info.data) and (info.data["env"] == EnvEnum.DEVELOPMENT):
            _dev.reload = True

        _dev = FrozenDevConfig(**_dev.model_dump())
        val = FrozenApiConfig(dev=_dev, **val.model_dump(exclude={"dev"}))
        return val

    @field_validator("challenge")
    @classmethod
    def _check_challenge(
        cls, val: ChallengeConfig, info: ValidationInfo
    ) -> ChallengeConfig:
        if "api" not in info.data:
            raise ValueError("Missing 'api' attribute in main config!")

        _devices_path = os.path.join(
            info.data.get("api").paths.configs_dir, val.devices_fname
        )

        if not os.path.isfile(_devices_path):
            raise FileNotFoundError(f"Not found '{_devices_path}' file!")

        _devices: list[dict] = []
        try:
            with open(_devices_path, "r", encoding="utf-8") as _file:
                _devices: list[dict] = json.load(_file)

            if not isinstance(_devices, list):
                raise ValueError(
                    f"'{_devices_path}' file format type {type(_devices)} is invalid, must be a <list>!"
                )

        except Exception:
            logger.error(f"Failed to load '{_devices_path}' file!")
            raise

        for _device in _devices:
            if not _device.get("pushcut_api_key"):
                _device["pushcut_api_key"] = val.pushcut_api_key

        val = ChallengeConfig(devices=_devices, **val.model_dump(exclude={"devices"}))
        return val

    @field_validator("logger")
    @classmethod
    def _check_logger(cls, val: LoggerConfigPM, info: ValidationInfo) -> LoggerConfigPM:
        if "api" in info.data:
            if not val.app_name:
                val.app_name = info.data["api"].slug
            elif "{api_slug}" in val.app_name:
                val.app_name = val.app_name.format(api_slug=info.data["api"].slug)

        _logs_dir_env = f"{ENV_PREFIX_API}LOGS_DIR"
        if _logs_dir_env in os.environ:
            val.file.logs_dir = os.getenv(_logs_dir_env)

        return val

    @model_validator(mode="after")
    def _check_required_envs(self) -> Self:
        _required_envs = [
            # f"{ENV_PREFIX_API}SECURITY_JWT_SECRET",
        ]

        if (self.env == EnvEnum.STAGING) or (self.env == EnvEnum.PRODUCTION):
            for _required_env in _required_envs:
                if _required_env not in os.environ:
                    raise ValueError(
                        f"Missing required '{_required_env}' environment variable for STAGING/PRODUCTION environment!"
                    )

        return self

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, env_nested_delimiter="__")


__all__ = ["MainConfig"]
