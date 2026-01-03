import datetime
from pydantic import Field, model_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from typing_extensions import Self

from .base import ENV_PREFIX
from .bittensor import BittensorConfig
from .internal_services import InternalServicesConfig

try:
    from ..__version__ import __version__
except ImportError:
    __version__ = "0.0.0"


class MainConfig(BaseSettings):
    TESTNET: bool = Field(
        default=False, description="Flag to indicate if running in testnet mode"
    )

    VERSION: str = Field(
        default=__version__,
        description="Version of the application in 'major.minor.patch' format",
    )
    SPEC_VERSION: int = Field(
        default=0,
        description="Specification version calculated from the version string",
    )

    N_CHALLENGES_PER_EPOCH: int = Field(
        default=1, description="Number of challenges per epoch", ge=1
    )
    SCORING_HOUR: int = Field(
        default=14,
        description="Hour of the day when scoring occurs (0-23)",
        ge=0,
        le=23,
    )

    CHALLENGE_SCORES_WEIGHT: float = Field(
        default=0.5, description="Weight of challenge scores", ge=0.0, le=1.0
    )
    ALPHA_BURN_WEIGHT: float = Field(
        default=0.5, description="Weight of alpha burning", ge=0.0, le=1.0
    )

    CHALLENGE_DOCKER_PORT: int = Field(
        default=10001,
        description="Port used for challenge Docker containers",
        ge=1,
        le=65535,
    )
    MINER_DOCKER_PORT: int = Field(
        default=10002,
        description="Port used for miner Docker containers",
        ge=1,
        le=65535,
    )

    REVEAL_INTERVAL: int = Field(
        default=3600 * 24,
        description="Time interval for revealing commits (seconds)",
        ge=1,
    )
    EPOCH_LENGTH: int = Field(
        default=1200, description="Length of an epoch in seconds", ge=1
    )
    MIN_VALIDATOR_STAKE: int = Field(
        default=10_000, description="Minimum validator stake required"
    )

    QUERY_TIMEOUT: int = Field(
        default=60, description="Timeout for queries in seconds", ge=1
    )

    STORAGE_API_URL: AnyHttpUrl = Field(
        default="https://storage-api.theredteam.io",
        description="Full URL for storing miners' work (auto-generated)",
    )
    BITTENSOR: BittensorConfig = Field(
        default_factory=BittensorConfig, description="Bittensor network configuration"
    )
    INTERNAL_SERVICES: InternalServicesConfig = Field(
        default_factory=InternalServicesConfig,
        description="Internal services configuration",
    )

    @model_validator(mode="after")
    def _check_all(self) -> Self:
        if self.TESTNET:
            self.REVEAL_INTERVAL = 30
            self.EPOCH_LENGTH = 30
            self.MIN_VALIDATOR_STAKE = -1

        return self

    @model_validator(mode="before")
    @classmethod
    def calculate_spec_version(cls, values):
        """Calculate specification version from version string."""
        version_str = values.get("VERSION", "0.0.1")
        try:
            major, minor, patch = (int(part) for part in version_str.split("."))
            values["SPEC_VERSION"] = (1000 * major) + (10 * minor) + patch
        except ValueError as e:
            raise ValueError(
                f"Invalid version format '{version_str}'. Expected 'major.minor.patch'."
            ) from e
        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        extra="ignore",
    )

    def is_commit_on_time(self, commit_timestamp: float) -> bool:
        """
        Validator do scoring every day at SCORING_HOUR.
        So the commit time should be submitted before the previous day's SCORING_HOUR.
        """
        if self.TESTNET:
            return True

        today_closed_time = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=self.SCORING_HOUR, minute=0, second=0, microsecond=0
        )
        previous_day_closed_time = today_closed_time - datetime.timedelta(days=1)
        return commit_timestamp < previous_day_closed_time.timestamp()


constants = MainConfig(VERSION=__version__)

__all__ = [
    "MainConfig",
    "constants",
]
