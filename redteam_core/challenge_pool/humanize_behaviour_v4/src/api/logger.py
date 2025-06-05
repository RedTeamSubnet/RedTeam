# -*- coding: utf-8 -*-

from pydantic import validate_call
from fastapi.concurrency import run_in_threadpool

from beans_logging import Logger, LoggerLoader
from beans_logging_fastapi import (
    add_http_file_handler,
    add_http_file_json_handler,
    http_file_format,
)

from api.core.constants import WarnEnum
from api.config import config


logger_loader = LoggerLoader(config=config.logger, auto_config_file=False)
logger: Logger = logger_loader.load()


def _http_file_format(record: dict) -> str:
    _format = http_file_format(
        record=record,
        msg_format=config.logger.extra.http_file_format,
        tz=config.logger.extra.http_file_tz,
    )
    return _format


if config.logger.extra.http_file_enabled:
    add_http_file_handler(
        logger_loader=logger_loader,
        log_path=config.logger.extra.http_log_path,
        err_path=config.logger.extra.http_err_path,
        formatter=_http_file_format,
    )

if config.logger.extra.http_json_enabled:
    add_http_file_json_handler(
        logger_loader=logger_loader,
        log_path=config.logger.extra.http_json_path,
        err_path=config.logger.extra.http_json_err_path,
    )


@validate_call
def log_mode(
    message: str, level: str = "INFO", warn_mode: WarnEnum = WarnEnum.ALWAYS
) -> None:
    """Log message with level and warn mode.

    Args:
        message   (str,          reqiured): Message to log.
        level     (LogLevelEnum, optional): Log level when warn mode is `WarnEnum.ALWAYS`. Defaults to "INFO".
        warn_mode (WarnEnum,     optional): Warn mode to use. Defaults to `WarnEnum.ALWAYS`.

    Raises:
        ValueError: If `level` is not a valid log level.
    """

    level = level.upper()
    if warn_mode == WarnEnum.ALWAYS:
        if level == "INFO":
            logger.info(message)
        elif level == "SUCCESS":
            logger.success(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "CRITICAL":
            logger.critical(message)
        elif level == "TRACE":
            logger.trace(message)
        else:
            raise ValueError(f"Unknown log level: '{level}'")

    elif warn_mode == WarnEnum.DEBUG:
        logger.debug(message)

    return


@validate_call
async def async_log_mode(
    message: str, level: str = "INFO", warn_mode: WarnEnum = WarnEnum.ALWAYS
) -> None:
    """Log message with level and warn mode in async mode.

    Args:
        message   (str     , required): Message to log.
        level     (str     , optional): Log level when warn mode is `WarnEnum.ALWAYS`. Defaults to "INFO".
        warn_mode (WarnEnum, optional): Warn mode to use. Defaults to `WarnEnum.ALWAYS`.
    """

    level = level.upper()
    if warn_mode == WarnEnum.ALWAYS:
        if level == "INFO":
            await run_in_threadpool(logger.info, message)
        elif level == "SUCCESS":
            await run_in_threadpool(logger.success, message)
        elif level == "WARNING":
            await run_in_threadpool(logger.warning, message)
        elif level == "ERROR":
            await run_in_threadpool(logger.error, message)
        elif level == "CRITICAL":
            await run_in_threadpool(logger.critical, message)
        elif level == "TRACE":
            await run_in_threadpool(logger.trace, message)
        else:
            raise ValueError(f"Unknown log level: '{level}'")

    elif warn_mode == WarnEnum.DEBUG:
        await run_in_threadpool(logger.debug, message)

    return


__all__ = [
    "logger_loader",
    "logger",
    "log_mode",
    "async_log_mode",
]
