# -*- coding: utf-8 -*-

from typing import Type, Tuple

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="allow", arbitrary_types_allowed=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return dotenv_settings, env_settings, init_settings, file_secret_settings


class FrozenBaseConfig(BaseConfig):
    model_config = SettingsConfigDict(frozen=True)


__all__ = ["BaseConfig", "FrozenBaseConfig"]
