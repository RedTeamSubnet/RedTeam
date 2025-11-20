from typing import List

from pydantic import Field, SecretStr, BaseModel, AnyHttpUrl
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX
from ._base import FrozenBaseConfig


class FrameworkImageConfig(BaseModel):
    name: str = Field(...)
    image: str = Field(...)


class ChallengeConfig(FrozenBaseConfig):
    api_key: SecretStr = Field(..., min_length=12, max_length=128)
    docker_ulimit: int = Field(...)
    # allowed_pip_pkg_dt: datetime = Field(...)
    allowed_file_exts: List[str] = Field(..., min_length=1)
    # pushcut_api_key: SecretStr = Field(..., min_length=8, max_length=128)
    # pushcut_shortcut: str = Field(...)
    # pushcut_timeout: int = Field(..., ge=1)
    # pushcut_server_id: Optional[str] = Field(default=None)
    # pushcut_web_url: AnyHttpUrl = Field(...)
    bot_timeout: int = Field(..., ge=1)
    framework_count: int = Field(..., ge=1)
    repeated_framework_count: int = Field(..., ge=1)
    framework_images: List[FrameworkImageConfig] = Field(...)
    result_endpoint: AnyHttpUrl = Field(...)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = [
    "FrameworkImageConfig",
    "ChallengeConfig",
]
