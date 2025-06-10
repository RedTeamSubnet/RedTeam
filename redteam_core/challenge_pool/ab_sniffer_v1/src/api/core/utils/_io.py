# -*- coding: utf-8 -*-

import os
import errno
import shutil
import hashlib
from typing import List

import aioshutil
import aiofiles.os
from pydantic import validate_call, conint, constr
from beans_logging import logger

from api.core.constants import WarnEnum, HashAlgoEnum


_path_max_length = 1024


## Async:
@validate_call
async def async_create_dir(
    create_dir: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Asynchronous create directory if `create_dir` doesn't exist.

    Args:
        create_dir (str, required): Create directory path.
        warn_mode  (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and directory already exists.
        OSError: If failed to create directory.
    """

    if not await aiofiles.os.path.isdir(create_dir):
        try:
            _message = f"Creating '{create_dir}' directory..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            await aiofiles.os.makedirs(create_dir)
        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{create_dir}' directory already exists!")
            else:
                logger.error(f"Failed to create '{create_dir}' directory!")
                raise

        _message = f"Successfully created '{create_dir}' directory."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.EEXIST, f"'{create_dir}' directory already exists!")

    return


@validate_call
async def async_remove_dir(
    remove_dir: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Asynchronous remove directory if `remove_dir` exists.

    Args:
        remove_dir (str, required): Remove directory path.
        warn_mode  (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and directory doesn't exist.
        OSError: If failed to remove directory.
    """

    if await aiofiles.os.path.isdir(remove_dir):
        try:
            _message = f"Removing '{remove_dir}' directory..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            await aioshutil.rmtree(remove_dir)
        except OSError as err:
            if (err.errno == errno.ENOENT) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{remove_dir}' directory doesn't exist!")
            else:
                logger.error(f"Failed to remove '{remove_dir}' directory!")
                raise

        _message = f"Successfully removed '{remove_dir}' directory."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.ENOENT, f"'{create_dir}' directory doesn't exist!")

    return


@validate_call
async def async_remove_dirs(
    remove_dirs: List[constr(strip_whitespace=True, min_length=1, max_length=_path_max_length)],  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Asynchronous remove directories if `remove_dirs` exists.

    Args:
        remove_dirs (List[str], required): Remove directories paths as list.
        warn_mode   (str      , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.
    """

    for _remove_dir in remove_dirs:
        await async_remove_dir(remove_dir=_remove_dir, warn_mode=warn_mode)

    return


@validate_call
async def async_remove_file(
    file_path: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Asynchronous remove file if `file_path` exists.

    Args:
        file_path (str, required): Remove file path.
        warn_mode (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and file doesn't exist.
        OSError: If failed to remove file.
    """

    if await aiofiles.os.path.isfile(file_path):
        try:
            _message = f"Removing '{file_path}' file..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            await aiofiles.os.remove(file_path)
        except OSError as err:
            if (err.errno == errno.ENOENT) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{file_path}' file doesn't exist!")
            else:
                logger.error(f"Failed to remove '{file_path}' file!")
                raise

        _message = f"Successfully removed '{file_path}' file."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.ENOENT, f"'{file_path}' file doesn't exist!")

    return


@validate_call
async def async_remove_files(
    file_paths: List[constr(strip_whitespace=True, min_length=1, max_length=_path_max_length)],  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Asynchronous remove files if `file_paths` exists.

    Args:
        file_paths (List[str], required): Remove file paths as list.
        warn_mode  (str      , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.
    """

    for _file_path in file_paths:
        await async_remove_file(file_path=_file_path, warn_mode=warn_mode)

    return


@validate_call
async def async_get_file_checksum(
    file_path: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    hash_method: HashAlgoEnum = HashAlgoEnum.md5,
    chunk_size: conint(ge=10) = 4096,  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> str:
    """Asynchronous get file checksum.

    Args:
        file_path   (str         , required): Target file path.
        hash_method (HashAlgoEnum, optional): Hash method. Defaults to `HashAlgoEnum.md5`.
        chunk_size  (int         , optional): Chunk size. Defaults to 4096.
        warn_mode   (str         , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and file doesn't exist.

    Returns:
        str: File checksum.
    """

    _file_checksum: str = None
    if await aiofiles.os.path.isfile(file_path):
        _file_hash = hashlib.new(hash_method.value)
        async with aiofiles.open(file_path, "rb") as _file:
            while True:
                _file_chunk = await _file.read(chunk_size)
                if not _file_chunk:
                    break
                _file_hash.update(_file_chunk)

        _file_checksum = _file_hash.hexdigest()
    else:
        _message = f"'{file_path}' file doesn't exist!"
        if warn_mode == WarnEnum.ALWAYS:
            logger.warning(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            raise OSError(errno.ENOENT, _message)

    return _file_checksum


## Sync:
@validate_call
def create_dir(
    create_dir: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Create directory if `create_dir` doesn't exist.

    Args:
        create_dir (str, required): Create directory path.
        warn_mode  (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and directory already exists.
        OSError: If failed to create directory.
    """

    if not os.path.isdir(create_dir):
        try:
            _message = f"Creating '{create_dir}' directory..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            os.makedirs(create_dir)
        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{create_dir}' directory already exists!")
            else:
                logger.error(f"Failed to create '{create_dir}' directory!")
                raise

        _message = f"Successfully created '{create_dir}' directory."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.EEXIST, f"'{create_dir}' directory already exists!")

    return


@validate_call
def remove_dir(
    remove_dir: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Remove directory if `remove_dir` exists.

    Args:
        remove_dir (str, required): Remove directory path.
        warn_mode  (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and directory doesn't exist.
        OSError: If failed to remove directory.
    """

    if os.path.isdir(remove_dir):
        try:
            _message = f"Removing '{remove_dir}' directory..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            shutil.rmtree(remove_dir)
        except OSError as err:
            if (err.errno == errno.ENOENT) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{remove_dir}' directory doesn't exist!")
            else:
                logger.error(f"Failed to remove '{remove_dir}' directory!")
                raise

        _message = f"Successfully removed '{remove_dir}' directory."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.ENOENT, f"'{create_dir}' directory doesn't exist!")

    return


@validate_call
def remove_dirs(
    remove_dirs: List[constr(strip_whitespace=True, min_length=1, max_length=_path_max_length)],  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Remove directories if `remove_dirs` exist.

    Args:
        remove_dirs (List[str], required): Remove directory paths as list.
        warn_mode   (str      , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.
    """

    for _remove_dir in remove_dirs:
        remove_dir(remove_dir=_remove_dir, warn_mode=warn_mode)

    return


@validate_call
def remove_file(
    file_path: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Remove file if `file_path` exists.

    Args:
        file_path (str, required): Remove file path.
        warn_mode (str, optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and file doesn't exist.
        OSError: If failed to remove file.
    """

    if os.path.isfile(file_path):
        try:
            _message = f"Removing '{file_path}' file..."
            if warn_mode == WarnEnum.ALWAYS:
                logger.info(_message)
            elif warn_mode == WarnEnum.DEBUG:
                logger.debug(_message)

            os.remove(file_path)
        except OSError as err:
            if (err.errno == errno.ENOENT) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{file_path}' file doesn't exist!")
            else:
                logger.error(f"Failed to remove '{file_path}' file!")
                raise

        _message = f"Successfully removed '{file_path}' file."
        if warn_mode == WarnEnum.ALWAYS:
            logger.success(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)

    elif warn_mode == WarnEnum.ERROR:
        raise OSError(errno.ENOENT, f"'{file_path}' file doesn't exist!")

    return


@validate_call
def remove_files(
    file_paths: List[constr(strip_whitespace=True, min_length=1, max_length=_path_max_length)],  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Remove files if `file_paths` exist.

    Args:
        file_paths (List[str], required): Remove file paths as list.
        warn_mode  (str      , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.
    """

    for _file_path in file_paths:
        remove_file(file_path=_file_path, warn_mode=warn_mode)

    return


@validate_call
def get_file_checksum(
    file_path: constr(strip_whitespace=True, min_length=1, max_length=_path_max_length),  # type: ignore
    hash_method: HashAlgoEnum = HashAlgoEnum.md5,
    chunk_size: conint(ge=10) = 4096,  # type: ignore
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> str:
    """Get file checksum.

    Args:
        file_path   (str         , required): Target file path.
        hash_method (HashAlgoEnum, optional): Hash method. Defaults to `HashAlgoEnum.md5`.
        chunk_size  (int         , optional): Chunk size. Defaults to 4096.
        warn_mode   (str         , optional): Warning message mode, for example: 'ERROR', 'ALWAYS', 'DEBUG', 'IGNORE'. Defaults to 'DEBUG'.

    Raises:
        OSError: When warning mode is set to ERROR and file doesn't exist.

    Returns:
        str: File checksum.
    """

    _file_checksum: str = None
    if os.path.isfile(file_path):
        _file_hash = hashlib.new(hash_method.value)
        with open(file_path, "rb") as _file:
            while True:
                _file_chunk = _file.read(chunk_size)
                if not _file_chunk:
                    break
                _file_hash.update(_file_chunk)

        _file_checksum = _file_hash.hexdigest()
    else:
        _message = f"'{file_path}' file doesn't exist!"
        if warn_mode == WarnEnum.ALWAYS:
            logger.warning(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            raise OSError(errno.ENOENT, _message)

    return _file_checksum


__all__ = [
    "async_create_dir",
    "async_remove_dir",
    "async_remove_dirs",
    "async_remove_file",
    "async_remove_files",
    "async_get_file_checksum",
    "create_dir",
    "remove_dir",
    "remove_dirs",
    "remove_file",
    "remove_files",
    "get_file_checksum",
]
