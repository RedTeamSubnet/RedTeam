import os
import datetime
from typing import Type, Tuple, Optional
from typing_extensions import Self

from dotenv import load_dotenv
from pydantic import Field, model_validator, AnyHttpUrl
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

from .__version__ import __version__
from .common import generate_constants_docs

load_dotenv(override=True)

ENV_PREFIX = "RT_"
ENV_PREFIX_BT = f"{ENV_PREFIX}BT_"
ENV_PREFIX_STORAGE_API = f"{ENV_PREFIX}STORAGE_API_"
ENV_PREFIX_REWARD_APP = f"{ENV_PREFIX}REWARD_APP_"
ENV_PREFIX_VALIDATOR = f"{ENV_PREFIX}VALIDATOR_"


##-----------------------------------------------------------------------------
## Base config classes:
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


##-----------------------------------------------------------------------------


class ValidatorConfig(BaseConfig):
    UPDATE_RATE_MINUTES: int = Field(default=60, description="Update rate in minutes.")
    UPDATE_BRANCH_NAME: str = Field(default="main", description="Update branch name.")

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_VALIDATOR)


class StorageApiConfig(BaseConfig):
    HTTP_SCHEME: str = Field(default="https")
    HOST: str = Field(default="storage-api.theredteam.io")
    PORT: int = Field(default=443)
    BASE_PATH: str = Field(default="")

    URL: Optional[AnyHttpUrl] = Field(
        default=None, description="URL for storing miners' work"
    )

    @model_validator(mode="after")
    def _check_all(self) -> Self:
        _storage_url_template = "{http_scheme}://{host}:{port}{base_path}"
        if not self.URL:
            self.URL = _storage_url_template.format(
                http_scheme=self.HTTP_SCHEME,
                host=self.HOST,
                port=self.PORT,
                base_path=self.BASE_PATH,
            )

        return self

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_STORAGE_API)


class RewardAppConfig(BaseConfig):
    HTTP_SCHEME: str = Field(default="https")
    HOST: str = Field(default="scoring-api.theredteam.io")
    PORT: int = Field(default=443)
    BASE_PATH: str = Field(default="")

    URL: Optional[AnyHttpUrl] = Field(
        default=None, description="URL for rewarding miners"
    )

    @model_validator(mode="after")
    def _check_all(self) -> Self:
        _reward_url_template = "{http_scheme}://{host}:{port}{base_path}"
        if not self.URL:
            self.URL = _reward_url_template.format(
                http_scheme=self.HTTP_SCHEME,
                host=self.HOST,
                port=self.PORT,
                base_path=self.BASE_PATH,
            )

        return self

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_REWARD_APP)


class MainConfig(BaseSettings):
    """
    Configuration constants for the application.
    """

    # Environment settings
    TESTNET: bool = Field(
        default=False,
        description="Flag to indicate if running in testnet mode.",
    )

    # Subnet settings
    SUBNET_IMMUNITY_PERIOD: int = Field(
        default=14400,
        description="Subnet immunity period in blocks (12 seconds per block).",
    )

    # Versioning
    VERSION: str = Field(
        default=__version__,
        description="Version of the application in 'major.minor.patch' format.",
    )
    SPEC_VERSION: int = Field(
        default=0,
        description="Specification version calculated from the version string.",
    )

    # Challenge settings
    N_CHALLENGES_PER_EPOCH: int = Field(
        default=100, description="Number of challenges per epoch."
    )
    SCORING_HOUR: int = Field(
        default=14, description="Hour of the day when scoring occurs (0-23)."
    )

    # Weighting settings
    CHALLENGE_SCORES_WEIGHT: float = Field(
        default=0.5, description="Weight of challenge scores."
    )
    # NEWLY_REGISTRATION_WEIGHT: float = Field(
    #     default=0.05, description="Weight of newly registration scores."
    # )
    # ALPHA_STAKE_WEIGHT: float = Field(
    #     default=0.05, description="Weight of alpha stake scores."
    # )
    ALPHA_BURN_WEIGHT: float = Field(
        default=0.5, description="Weight of alpha burning."
    )

    # Network settings
    CHALLENGE_DOCKER_PORT: int = Field(
        default=10001, description="Port used for challenge Docker containers."
    )
    MINER_DOCKER_PORT: int = Field(
        default=10002, description="Port used for miner Docker containers."
    )

    # Time intervals (in seconds)
    REVEAL_INTERVAL: int = Field(
        default=3600 * 24, description="Time interval for revealing commits."
    )
    EPOCH_LENGTH: int = Field(
        default=1200, description="Length of an epoch in seconds."
    )
    MIN_VALIDATOR_STAKE: int = Field(
        default=10_000, description="Minimum validator stake required."
    )

    # Query settings
    QUERY_TIMEOUT: int = Field(
        default=60, description="Timeout for queries in seconds."
    )

    STORAGE_API: StorageApiConfig = Field(default_factory=StorageApiConfig)
    REWARD_APP: RewardAppConfig = Field(default_factory=RewardAppConfig)
    VALIDATOR: ValidatorConfig = Field(default_factory=ValidatorConfig)

    # Centralized API settings
    # STORAGE_URL: AnyUrl = Field(
    #     default="http://storage.redteam.technology/storage",
    #     description="URL for storing miners' work",
    # )
    # REWARDING_URL: AnyUrl = Field(
    #     default="http://storage.redteam.technology/rewarding",
    #     description="URL for rewarding miners",
    # )

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
        """
        Calculates the specification version as an integer based on the version string.
        """
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
        # validate_assignment=True,
        env_file=".env",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        extra="ignore",
    )

    # @model_validator(mode="before")
    # @classmethod
    # def adjust_for_testnet(cls, values):
    #     """
    #     Adjusts certain constants based on whether TESTNET mode is enabled.

    #     Args:
    #         values: Dictionary of field values.

    #     Returns:
    #         dict: The adjusted values dictionary.
    #     """
    #     testnet = os.environ.get("TESTNET", "")
    #     is_testnet = testnet.lower() in ("1", "true", "yes")
    #     print(f"Testnet mode: {is_testnet}, {testnet}")
    #     if is_testnet:
    #         print("Adjusting constants for testnet mode.")
    #         values["REVEAL_INTERVAL"] = 30
    #         values["EPOCH_LENGTH"] = 30
    #         values["MIN_VALIDATOR_STAKE"] = -1
    #     return values

    def is_commit_on_time(self, commit_timestamp: float) -> bool:
        """
        Validator do scoring every day at SCORING_HOUR.
        So the commit time should be submitted before the previous day's SCORING_HOUR.
        """
        today_closed_time = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=self.SCORING_HOUR, minute=0, second=0, microsecond=0
        )
        previous_day_closed_time = today_closed_time - datetime.timedelta(days=1)
        return commit_timestamp < previous_day_closed_time.timestamp()


constants = MainConfig(VERSION=__version__)


if __name__ == "__main__":
    from termcolor import colored

    def print_with_colors(content: str):
        """
        Prints the content with basic colors using termcolor.

        Args:
            content (str): The content to print.
        """
        print(colored(content, "cyan"))

    markdown_content = generate_constants_docs(MainConfig)

    print_with_colors(markdown_content)


__all__ = [
    "MainConfig",
    "constants",
]
