import os
from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict
from typing_extensions import Self

from .base import BaseConfig, ENV_PREFIX_BT


class BittensorConfig(BaseConfig):
    """
    Complete Bittensor configuration.
    Aggregates wallet, subtensor, axon, and logging settings.
    """

    SUBTENSOR_NETWORK: str = Field(
        default="wss://entrypoint-finney.opentensor.ai:443",
        description="Bittensor network to connect to",
    )
    LOGGING_LEVEL: str = Field(
        default="INFO", description="Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )
    SUBNET_NETUID: int = Field(default=61, description="Subnet NetUID", gt=0, lt=256)

    @model_validator(mode="after")
    def validate_level(self) -> Self:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = self.LOGGING_LEVEL.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"Log level must be one of {sorted(valid_levels)}, got '{self.LOGGING_LEVEL}'"
            )
        self.LOGGING_LEVEL = v_upper
        return self

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_BT)


__all__ = [
    "BittensorWalletConfig",
    "BittensorSubtensorConfig",
    "BittensorAxonConfig",
    "BittensorConfig",
]
