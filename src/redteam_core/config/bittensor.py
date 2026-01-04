import os
from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from .base import BaseConfig, ENV_PREFIX_SUBNET, ENV_PREFIX_BT


class BittensorSubnetConfig(BaseConfig):
    NETUID: int = Field(default=61, description="Subnet UID (required)", gt=0)
    CACHE_DIR: str = Field(
        default="/var/lib/agent-validator/cache", description="Cache directory path"
    )

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX_SUBNET,
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    @field_validator("CACHE_DIR")
    @classmethod
    def validate_cache_dir(cls, v: str) -> str:
        """Ensure cache directory exists and is writable."""
        expanded = os.path.expanduser(v)
        os.makedirs(expanded, exist_ok=True)
        if not os.access(expanded, os.W_OK):
            raise ValueError(f"Cache directory not writable: {expanded}")
        return v


class BittensorConfig(BaseConfig):
    """
    Complete Bittensor configuration.
    Aggregates wallet, subtensor, axon, and logging settings.
    """

    SUBTENSOR_NETWORK: str = Field(
        default="wss://entrypoint-finney.opentensor.ai:443",
        description="Bittensor network to connect to",
    )
    AXON_PORT: int = Field(
        default=8091, description="Port for the axon to listen on", ge=1, le=65535
    )
    SUBNET: BittensorSubnetConfig = Field(
        default_factory=BittensorSubnetConfig,
        description="Subnet-specific configuration",
    )
    LOGGING_LEVEL: str = Field(
        default="INFO", description="Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )

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
    "BittensorLoggingConfig",
    "BittensorConfig",
]
