import os
from typing import Optional
from pydantic import Field, AnyHttpUrl
from pydantic_settings import SettingsConfigDict

from .base import BaseConfig, ENV_PREFIX_INTERNAL_SERVICES


class InternalServicesConfig(BaseConfig):
    """
    Internal services configuration.

    Environment Variables:
        RT_INS_KEY: API key for authentication (default: default_api_key)
        RT_INS_HTTP_SCHEME: HTTP scheme (default: https)
        RT_INS_HOST: API host (default: scoring-api.theredteam.io)
        RT_INS_PORT: API port (default: 443)
        RT_INS_BASE_PATH: Base path for API (default: /api/v1/)
        RT_INS_URL: Full URL (auto-generated if not set)
    """

    API_KEY: str = Field(
        default=os.getenv("RT_INTERNAL_SERVICES_API_KEY", "default_api_key"),
        description="API key for internal services authentication",
    )
    URL: Optional[AnyHttpUrl] = Field(
        default=None, description="Full URL for internal services (auto-generated)"
    )

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_INTERNAL_SERVICES)


__all__ = ["InternalServicesConfig"]
