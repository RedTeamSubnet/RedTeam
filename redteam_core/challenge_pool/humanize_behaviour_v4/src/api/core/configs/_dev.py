# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional

from pydantic import Field, constr, model_validator
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_API
from ._base import BaseConfig


class DevConfig(BaseConfig):
    reload: bool = Field(...)
    reload_includes: Optional[
        List[constr(strip_whitespace=True, min_length=1, max_length=256)]  # type: ignore
    ] = Field(default=None)
    reload_excludes: Optional[
        List[constr(strip_whitespace=True, min_length=1, max_length=256)]  # type: ignore
    ] = Field(default=None)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX_API}DEV_")


class FrozenDevConfig(DevConfig):
    @model_validator(mode="before")
    @classmethod
    def _check_all(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["reload"]:
            values["reload_includes"] = None
            values["reload_excludes"] = None

        return values

    model_config = SettingsConfigDict(frozen=True)


__all__ = ["DevConfig", "FrozenDevConfig"]
