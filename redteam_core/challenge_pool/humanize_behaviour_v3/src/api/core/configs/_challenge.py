# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List, Optional, Dict, Union

from pydantic import Field, constr
from pydantic_settings import SettingsConfigDict

from api.core.constants import ALPHANUM_HOST_REGEX, ENV_PREFIX
from ._base import FrozenBaseConfig


class ChallengeConfig(FrozenBaseConfig):
    n_ch_per_epoch: int = Field(...)
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
    window_width: int = Field(..., ge=20, le=12000)
    window_height: int = Field(..., ge=20, le=12000)
    n_checkboxes: int = Field(..., ge=2, le=100)
    cb_min_distance: int = Field(..., ge=1, le=1000)
    cb_gen_max_factor: int = Field(..., ge=2, le=100)
    cb_size: int = Field(..., ge=10, le=100)
    cb_exclude_areas: Optional[List[Dict[str, int]]] = Field(default=None)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = ["ChallengeConfig"]
