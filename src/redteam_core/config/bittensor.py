import os
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

from .base import BaseConfig, ENV_PREFIX_SUBNET, ENV_PREFIX_BT


class BittensorSubnetConfig(BaseConfig):
    NETUID: int = Field(..., description="Subnet UID (required)", gt=0)
    CACHE_DIR: str = Field(default="./.cache/", description="Cache directory path")
    HF_REPO_ID: str = Field(
        default="redteamsubnet61/storage",
        description="Hugging Face repository ID for storage",
    )
    USE_CENTRALIZED_SCORING: bool = Field(
        default=False,
        description="Use centralized scoring service instead of local scoring",
    )

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX_SUBNET,
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    @field_validator("cache_dir")
    @classmethod
    def validate_cache_dir(cls, v: str) -> str:
        """Ensure cache directory exists and is writable."""
        expanded = os.path.expanduser(v)
        os.makedirs(expanded, exist_ok=True)
        if not os.access(expanded, os.W_OK):
            raise ValueError(f"Cache directory not writable: {expanded}")
        return v


class BittensorLoggingConfig(BaseConfig):

    DIR: str = Field(default="~/.bittensor/logs", description="Directory for log files")
    LEVEL: str = Field(
        default="INFO", description="Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}, got '{v}'")
        return v_upper

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX_BT}LOGGING_")


class BittensorConfig(BaseConfig):
    """
    Complete Bittensor configuration.
    Aggregates wallet, subtensor, axon, and logging settings.
    """

    SUBTENSOR_NETWORK: str = Field(
        default="finney", description="Bittensor network to connect to"
    )
    AXON_PORT: int = Field(
        default=8091, description="Port for the axon to listen on", ge=1, le=65535
    )

    LOGGING: BittensorLoggingConfig = Field(
        default_factory=BittensorLoggingConfig, description="Logging configuration"
    )
    SUBNET: BittensorSubnetConfig = Field(
        default_factory=BittensorSubnetConfig,
        description="Subnet-specific configuration",
    )

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_BT)


__all__ = [
    "BittensorWalletConfig",
    "BittensorSubtensorConfig",
    "BittensorAxonConfig",
    "BittensorLoggingConfig",
    "BittensorConfig",
]
