# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List, Optional, Dict, Union, Annotated

from pydantic import Field, constr, BaseModel
from pydantic_settings import SettingsConfigDict

from api.core.constants import ALPHANUM_HOST_REGEX, ENV_PREFIX
from ._base import FrozenBaseConfig


class FrameworkImage(BaseModel):
    framework_name: Annotated[str, constr(strip_whitespace=True, min_length=1)] = Field(
        ...
    )
    image: str = Field(...)


class ChallengeConfig(FrozenBaseConfig):
    docker_ulimit: int = Field(...)
    allowed_pip_pkg_dt: datetime = Field(...)
    allowed_file_exts: List[
        constr(
            strip_whitespace=True,
            min_length=2,
            max_length=16,
            pattern=ALPHANUM_HOST_REGEX,
        )  # type: ignore
    ] = Field(..., min_length=1)
    bot_timeout: int = Field(..., ge=1)
    framework_count: int = Field(..., ge=1)
    repeated_framework_count: int = Field(..., ge=1)
    framework_images: List[FrameworkImage] = Field(...)
    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = ["ChallengeConfig"]
