# -*- coding: utf-8 -*-

from enum import Enum
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    constr,
    conint,
    SecretStr,
    IPvAnyAddress,
    AnyHttpUrl,
)
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX
from ._base import FrozenBaseConfig


class DeviceStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DeviceStateEnum(str, Enum):
    NOT_SET = "NOT_SET"
    READY = "READY"
    RUNNING = "RUNNING"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class DevicePM(BaseModel):
    id: conint(gt=0) = Field(...)  # type: ignore
    ts_node_id: constr(strip_whitespace=True, min_length=2, max_length=64) = Field(...)  # type: ignore
    ts_name: constr(strip_whitespace=True, min_length=2, max_length=64) = Field(...)  # type: ignore
    ts_ip: IPvAnyAddress = Field(...)
    pushcut_id: constr(strip_whitespace=True, min_length=2, max_length=64) = Field(...)  # type: ignore
    pushcut_api_key: Optional[SecretStr] = Field(
        default=None, min_length=8, max_length=128
    )
    pushcut_server_id: Optional[constr(strip_whitespace=True, min_length=2, max_length=128)] = Field(default=None)  # type: ignore
    device_model: Optional[constr(strip_whitespace=True, min_length=2, max_length=64)] = Field(default=None)  # type: ignore
    fingerprint: Optional[constr(strip_whitespace=True, min_length=2, max_length=256)] = Field(default=None)  # type: ignore
    state: DeviceStateEnum = Field(default=DeviceStateEnum.NOT_SET)
    status: DeviceStatusEnum = Field(default=DeviceStatusEnum.ACTIVE)


class DeviceConfig(DevicePM, FrozenBaseConfig):
    pass


class FragmentationThresholds(BaseModel):
    inconsistency_pct: float = Field(...)
    frag_pct: float = Field(...)


class CollisionThresholds(BaseModel):
    soft_pct: float = Field(...)
    hard_pct: float = Field(...)


class ThresholdsConfig(BaseModel):
    fragmentation: FragmentationThresholds = Field(...)
    collision: CollisionThresholds = Field(...)


class WeightsConfig(BaseModel):
    fragmentation: float = Field(...)
    soft_collision: float = Field(...)
    hard_collision: float = Field(...)


class ScoringConfig(FrozenBaseConfig):
    weights: WeightsConfig = Field(...)
    thresholds: ThresholdsConfig = Field(...)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}SCORING_")


class ChallengeConfig(FrozenBaseConfig):
    api_key: SecretStr = Field(..., min_length=8, max_length=128)
    fp_js_fname: constr(strip_whitespace=True, min_length=2, max_length=256) = Field(  # type: ignore
        ...
    )
    ts_api_token: SecretStr = Field(..., min_length=8, max_length=128)
    ts_tailnet: constr(strip_whitespace=True, min_length=2, max_length=256) = Field(...)  # type: ignore
    ts_device_tag: constr(strip_whitespace=True, min_length=2, max_length=64) = Field(  # type: ignore
        ...
    )
    ts_static_ip: IPvAnyAddress = Field(...)
    change_ts_ip: bool = Field(...)
    pushcut_api_key: SecretStr = Field(..., min_length=8, max_length=128)
    pushcut_shortcut: constr(strip_whitespace=True, min_length=2, max_length=128) = Field(  # type: ignore
        ...
    )
    pushcut_timeout: conint(ge=1) | constr(  # type: ignore
        strip_whitespace=True, min_length=1, max_length=8
    ) = Field(...)
    n_repeat: conint(ge=1) = Field(...)  # type: ignore
    random_seed: Optional[int] = Field(default=None)
    fp_timeout: conint(ge=1) = Field(...)  # type: ignore
    proxy_inter_base_url: AnyHttpUrl = Field(...)
    proxy_exter_base_url: AnyHttpUrl = Field(...)
    devices_fname: constr(strip_whitespace=True, min_length=2, max_length=256) = Field(  # type: ignore
        ...
    )
    devices: list[DeviceConfig] = Field(default_factory=list)
    scoring: ScoringConfig = Field(...)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX}CHALLENGE_")


__all__ = [
    "ChallengeConfig",
    "DeviceConfig",
    "DevicePM",
    "DeviceStatusEnum",
    "DeviceStateEnum",
]
