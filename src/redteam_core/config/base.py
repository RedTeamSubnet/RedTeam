from typing import Type, Tuple
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

ENV_PREFIX = "RT_"
ENV_PREFIX_BT = f"{ENV_PREFIX}BT_"
ENV_PREFIX_SUBNET = f"{ENV_PREFIX_BT}SUBNET_"
ENV_PREFIX_BTCLI = f"{ENV_PREFIX}BTCLI_"
ENV_PREFIX_STORAGE_API = f"{ENV_PREFIX}STORAGE_API_"
ENV_PREFIX_SCORING_API = f"{ENV_PREFIX}SCORING_API_"
ENV_PREFIX_INTERNAL_SERVICES = f"{ENV_PREFIX}INS_"
ENV_PREFIX_VALIDATOR = f"{ENV_PREFIX}VALIDATOR_"
ENV_PREFIX_MINER = f"{ENV_PREFIX}MINER_"


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

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


__all__ = [
    "BaseConfig",
    "FrozenBaseConfig",
    "ENV_PREFIX",
    "ENV_PREFIX_BT",
    "ENV_PREFIX_BTCLI",
    "ENV_PREFIX_SUBNET",
    "ENV_PREFIX_STORAGE_API",
    "ENV_PREFIX_SCORING_API",
    "ENV_PREFIX_INTERNAL_SERVICES",
    "ENV_PREFIX_VALIDATOR",
]
