import os
import datetime

from pydantic import Field, model_validator, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from .__version__ import __version__
from .common import generate_constants_docs


ENV_PREFIX = "RT_"


class Constants(BaseSettings):
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
        default=0.45, description="Weight of challenge scores."
    )
    # NEWLY_REGISTRATION_WEIGHT: float = Field(
    #     default=0.05, description="Weight of newly registration scores."
    # )
    ALPHA_STAKE_WEIGHT: float = Field(
        default=0.05, description="Weight of alpha stake scores."
    )
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
        default=3600, description="Length of an epoch in seconds."
    )
    MIN_VALIDATOR_STAKE: int = Field(
        default=10_000, description="Minimum validator stake required."
    )

    # Query settings
    QUERY_TIMEOUT: int = Field(
        default=60, description="Timeout for queries in seconds."
    )

    # Centralized API settings
    STORAGE_URL: AnyUrl = Field(
        default="http://storage.redteam.technology/storage",
        description="URL for storing miners' work",
    )
    REWARDING_URL: AnyUrl = Field(
        default="http://storage.redteam.technology/rewarding",
        description="URL for rewarding miners",
    )

    model_config = SettingsConfigDict(
        validate_assignment=True,
        env_file=".env",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        extra="allow",
    )

    @model_validator(mode="before")
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

    @model_validator(mode="before")
    def adjust_for_testnet(cls, values):
        """
        Adjusts certain constants based on whether TESTNET mode is enabled.

        Args:
            values: Dictionary of field values.

        Returns:
            dict: The adjusted values dictionary.
        """
        testnet = os.environ.get("TESTNET", "")
        is_testnet = testnet.lower() in ("1", "true", "yes")
        print(f"Testnet mode: {is_testnet}, {testnet}")
        if is_testnet:
            print("Adjusting constants for testnet mode.")
            values["REVEAL_INTERVAL"] = 30
            values["EPOCH_LENGTH"] = 30
            values["MIN_VALIDATOR_STAKE"] = -1
        return values

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


constants = Constants(VERSION=__version__)


if __name__ == "__main__":
    from termcolor import colored

    def print_with_colors(content: str):
        """
        Prints the content with basic colors using termcolor.

        Args:
            content (str): The content to print.
        """
        print(colored(content, "cyan"))

    markdown_content = generate_constants_docs(Constants)

    print_with_colors(markdown_content)


__all__ = [
    "constants",
    "Constants",
]
