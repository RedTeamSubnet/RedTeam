# -*- coding: utf-8 -*-

import time
from enum import Enum
from typing import Union, Optional
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, tzinfo, timedelta

from pydantic import validate_call, constr, conint
from beans_logging import logger

from api.core.constants import WarnEnum


class TSUnitEnum(str, Enum):
    SECONDS = "SECONDS"
    MILLISECONDS = "MILLISECONDS"
    MICROSECONDS = "MICROSECONDS"
    NANOSECONDS = "NANOSECONDS"


@validate_call(config={"arbitrary_types_allowed": True})
def add_tzinfo(dt: datetime, tz: Union[ZoneInfo, tzinfo, str]) -> datetime:
    """Add or replace timezone info to datetime object.

    Args:
        dt (datetime                    , required): Datetime object.
        tz (Union[ZoneInfo, tzinfo, str], required): Timezone info.

    Returns:
        datetime: Datetime object with timezone info.
    """

    if isinstance(tz, str):
        tz = ZoneInfo(tz)

    dt = dt.replace(tzinfo=tz)
    return dt


@validate_call
def datetime_to_iso(
    dt: datetime,
    sep: constr(max_length=8) = "T",  # type: ignore
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> str:
    """Convert datetime object to ISO 8601 format.

    Args:
        dt        (datetime, required): Datetime object.
        sep       (str     , optional): Separator between date and time. Defaults to "T".
        warn_mode (WarnEnum, optional): Warning mode. Defaults to WarnEnum.IGNORE.

    Raises:
        ValueError: If `dt` argument doesn't have any timezone info and `warn_mode` is set to WarnEnum.ERROR.

    Returns:
        str: Datetime string in ISO 8601 format.
    """

    if not dt.tzinfo:
        _message = "Not found any timezone info in `dt` argument, assuming it's UTC timezone..."
        if warn_mode == WarnEnum.ALWAYS:
            logger.warning(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            _message = "Not found any timezone info in `dt` argument!"
            logger.error(_message)
            raise ValueError(_message)

        dt = add_tzinfo(dt=dt, tz="UTC")

    _dt_str = dt.isoformat(sep=sep, timespec="milliseconds")
    return _dt_str


@validate_call(config={"arbitrary_types_allowed": True})
def convert_tz(
    dt: datetime,
    tz: Union[ZoneInfo, tzinfo, str],
    warn_mode: WarnEnum = WarnEnum.ALWAYS,
) -> datetime:
    """Convert datetime object to another timezone.

    Args:
        dt        (datetime                    , required): Datetime object to convert.
        tz        (Union[ZoneInfo, tzinfo, str], required): Timezone info to convert.
        warn_mode (WarnEnum                    , optional): Warning mode. Defaults to WarnEnum.ALWAYS.

    Raises:
        ValueError: If `dt` argument doesn't have any timezone info and `warn_mode` is set to WarnEnum.ERROR.

    Returns:
        datetime: Datetime object which has been converted to another timezone.
    """

    if not dt.tzinfo:
        _message = "Not found any timezone info in `dt` argument, assuming it's UTC timezone..."
        if warn_mode == WarnEnum.ALWAYS:
            logger.warning(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            _message = "Not found any timezone info in `dt` argument!"
            logger.error(_message)
            raise ValueError(_message)

        dt = add_tzinfo(dt=dt, tz="UTC")

    if isinstance(tz, str):
        tz = ZoneInfo(tz)

    dt = dt.astimezone(tz=tz)
    return dt


def now_utc_dt() -> datetime:
    """Get current datetime in UTC timezone with tzinfo.

    Returns:
        datetime: Current datetime in UTC timezone with tzinfo.
    """

    _utc_dt = datetime.now(tz=timezone.utc)
    return _utc_dt


def now_local_dt() -> datetime:
    """Get current datetime in local timezone with tzinfo.

    Returns:
        datetime: Current datetime in local timezone with tzinfo.
    """

    _local_dt = datetime.now().astimezone()
    return _local_dt


@validate_call(config={"arbitrary_types_allowed": True})
def now_dt(tz: Union[ZoneInfo, tzinfo, str]) -> datetime:
    """Get current datetime in specified timezone with tzinfo.

    Args:
        tz (Union[ZoneInfo, tzinfo, str], required): Timezone info.

    Returns:
        datetime: Current datetime in specified timezone with tzinfo.
    """

    _dt = now_utc_dt()
    _dt = convert_tz(dt=_dt, tz=tz)
    return _dt


@validate_call
def now_ts(unit: TSUnitEnum = TSUnitEnum.SECONDS) -> int:
    """Get current timestamp in UTC timezone.

    Args:
        unit (TSUnitEnum, optional): Type of timestamp unit. Defaults to `TSUnitEnum.SECONDS`.

    Returns:
        int: Current timestamp.
    """

    _now_ts: int = None
    if unit == TSUnitEnum.SECONDS:
        _now_ts = int(time.time())
    elif unit == TSUnitEnum.MILLISECONDS:
        _now_ts = int(_now_ts * 1000)
    elif unit == TSUnitEnum.MICROSECONDS:
        _now_ts = int(time.time_ns() / 1000)
    elif unit == TSUnitEnum.NANOSECONDS:
        _now_ts = int(time.time_ns())

    return _now_ts


@validate_call
def convert_ts(dt: datetime, unit: TSUnitEnum = TSUnitEnum.SECONDS) -> int:
    """Convert datetime to timestamp.

    Args:
        dt   (datetime  , required): Datetime object to convert.
        unit (TSUnitEnum, optional): Type of timestamp unit. Defaults to `TSUnitEnum.SECONDS`.

    Returns:
        int: Converted timestamp.
    """

    _ts: int = None
    if unit == TSUnitEnum.SECONDS:
        _ts = int(dt.timestamp())
    elif unit == TSUnitEnum.MILLISECONDS:
        _ts = int(dt.timestamp() * 1000)
    elif unit == TSUnitEnum.MICROSECONDS:
        _ts = int(dt.timestamp() * 1000000)
    elif unit == TSUnitEnum.NANOSECONDS:
        _ts = int(dt.timestamp() * 1000000000)

    return _ts


@validate_call(config={"arbitrary_types_allowed": True})
def calc_future_dt(
    delta: Union[timedelta, conint(ge=1)],  # type: ignore
    dt: Optional[datetime] = None,
    tz: Union[ZoneInfo, tzinfo, str, None] = None,
) -> datetime:
    """Calculate future datetime by adding delta time to current or specified datetime.

    Args:
        delta (Union[timedelta, int]             , required): Delta time to add to current or specified datetime.
        dt    (Optional[datetime]                , optional): Datetime before adding delta time. Defaults to None.
        tz    (Union[ZoneInfo, tzinfo, str, None], optional): Timezone info. Defaults to None.

    Returns:
        datetime: Calculated future datetime.
    """

    if not dt:
        dt = now_utc_dt()

    if tz:
        dt = convert_tz(dt=dt, tz=tz)

    if isinstance(delta, int):
        delta = timedelta(seconds=delta)

    _future_dt = dt + delta
    return _future_dt


__all__ = [
    "add_tzinfo",
    "datetime_to_iso",
    "convert_tz",
    "now_utc_dt",
    "now_local_dt",
    "now_dt",
    "now_ts",
    "convert_ts",
    "calc_future_dt",
]
