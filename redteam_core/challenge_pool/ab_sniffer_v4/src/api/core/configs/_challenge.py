# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List, Optional, Dict, Union, Annotated

from pydantic import AnyHttpUrl, Field, IPvAnyAddress, SecretStr, BaseModel
from pydantic_settings import SettingsConfigDict

from api.core.constants import ALPHANUM_HOST_REGEX, ENV_PREFIX
from ._base import FrozenBaseConfig


class FrameworkImage(BaseModel):
    framework_name: Annotated[str, Field(min_length=1, strip_whitespace=True)] = Field(
        ...
    )
    image: str = Field(...)


class ChallengeConfig(FrozenBaseConfig):
    docker_ulimit: int = Field(...)
    allowed_pip_pkg_dt: datetime = Field(...)
    allowed_file_exts: List[
        Annotated[
            str,
            Field(
                min_length=2,
                max_length=16,
                strip_whitespace=True,
                pattern=ALPHANUM_HOST_REGEX,
            ),
        ]
    ] = Field(..., min_length=1)
    pushcut_api_key: SecretStr = Field(..., min_length=8, max_length=128)
    pushcut_shortcut: Annotated[
        str, Field(min_length=2, max_length=128, strip_whitespace=True)
    ] = Field(...)
    pushcut_timeout: int = Field(..., ge=1)
    pushcut_server_id: Optional[
        Annotated[str, Field(strip_whitespace=True, min_length=2, max_length=128)]
    ] = Field(default=None)
    pushcut_web_url: AnyHttpUrl = Field(...)
    bot_timeout: int = Field(..., ge=1)
    framework_count: int = Field(..., ge=1)
    repeated_framework_count: int = Field(..., ge=1)
    framework_images: List[FrameworkImage] = Field(...)
    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = ["ChallengeConfig"]
