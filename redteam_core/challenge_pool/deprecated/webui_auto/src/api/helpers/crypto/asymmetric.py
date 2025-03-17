# -*- coding: utf-8 -*-

import os
import errno
import base64
from typing import Tuple, Union

import aiofiles
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.types import (
    PrivateKeyTypes,
    PublicKeyTypes,
)
from pydantic import validate_call
from beans_logging import logger

from api.constants import WarnEnum
from api import utils


@validate_call
async def async_create_keys(
    asymmetric_keys_dir: str,
    key_size: int,
    private_key_fname: str,
    public_key_fname: str,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Async create asymmetric keys and save them to files.

    Args:
        asymmetric_keys_dir (str     , required): Asymmetric keys directory.
        key_size            (int     , required): Asymmetric key size.
        private_key_fname   (str     , required): Asymmetric private key filename.
        public_key_fname    (str     , required): Asymmetric public key filename.
        warn_mode           (WarnEnum, optional): Warning mode. Defaults to WarnEnum.DEBUG.

    Raises:
        OSError: If failed to create asymmetric keys.
    """

    _private_key_path = os.path.join(asymmetric_keys_dir, private_key_fname)
    _public_key_path = os.path.join(asymmetric_keys_dir, public_key_fname)
    if await aiofiles.os.path.isfile(
        _private_key_path
    ) and await aiofiles.os.path.isfile(_public_key_path):
        return

    _private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )
    _public_key = _private_key.public_key()

    _private_pem = _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    _public_pem = _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    await utils.async_create_dir(create_dir=asymmetric_keys_dir, warn_mode=warn_mode)

    if not await aiofiles.os.path.isfile(_private_key_path):
        try:
            async with aiofiles.open(_private_key_path, "wb") as _private_key_file:
                await _private_key_file.write(_private_pem)

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_private_key_path}' private key already exists!")
            else:
                logger.error(f"Failed to create '{_private_key_path}' private key!")
                raise

    if not await aiofiles.os.path.isfile(_public_key_path):
        try:
            async with aiofiles.open(_public_key_path, "wb") as _public_key_file:
                await _public_key_file.write(_public_pem)

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_public_key_path}' public key already exists!")
            else:
                logger.error(f"Failed to create '{_public_key_path}' public key!")
                raise

    return


@validate_call
async def async_get_private_key(
    private_key_path: str, as_str: bool = False
) -> Union[PrivateKeyTypes, str]:
    """Async read asymmetric private key from file.

    Args:
        private_key_path (str , required): Asymmetric private key path.
        as_str           (bool, optional): Return private key as string. Defaults to False.

    Raises:
        FileNotFoundError: If Asymmetric private key file not found.

    Returns:
        Union[PrivateKeyTypes, str]: Asymmetric private key.
    """

    if not await aiofiles.os.path.isfile(private_key_path):
        raise FileNotFoundError(f"Not found '{private_key_path}' private key!")

    _private_key: PrivateKeyTypes = None
    async with aiofiles.open(private_key_path, "rb") as _private_key_file:
        _private_key_bytes: bytes = await _private_key_file.read()
        _private_key: PrivateKeyTypes = serialization.load_pem_private_key(
            _private_key_bytes, password=None, backend=default_backend()
        )

    if as_str:
        _private_key = _private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    return _private_key


@validate_call
async def async_get_public_key(
    public_key_path: str, as_str: bool = False
) -> Union[PublicKeyTypes, str]:
    """Async read asymmetric public key from file.

    Args:
        public_key_path (str , required): Asymmetric public key path.
        as_str          (bool, optional): Return public key as string. Defaults to False.

    Raises:
        FileNotFoundError: If asymmetric public key file not found.

    Returns:
        Union[PublicKeyTypes, str]: Asymmetric public key.
    """

    if not await aiofiles.os.path.isfile(public_key_path):
        raise FileNotFoundError(f"Not found '{public_key_path}' public key!")

    _public_key: PublicKeyTypes = None
    async with aiofiles.open(public_key_path, "rb") as _public_key_file:
        _public_key_bytes: bytes = await _public_key_file.read()
        _public_key: PublicKeyTypes = serialization.load_pem_public_key(
            _public_key_bytes, backend=default_backend()
        )

    if as_str:
        _public_key = _public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    return _public_key


@validate_call
async def async_get_keys(
    private_key_path: str, public_key_path: str, as_str: bool = False
) -> Tuple[Union[PrivateKeyTypes, str], Union[PublicKeyTypes, str]]:
    """Async read asymmetric keys from file.

    Args:
        private_key_path (str , required): Asymmetric private key path.
        public_key_path  (str , required): Asymmetric public key path.
        as_str           (bool, optional): Return keys as strings. Defaults to False.

    Returns:
        Tuple[Union[PrivateKeyTypes, str], Union[PublicKeyTypes, str]]: Private and public keys.
    """

    _private_key = await async_get_private_key(
        private_key_path=private_key_path, as_str=as_str
    )
    _public_key = await async_get_public_key(
        public_key_path=public_key_path, as_str=as_str
    )

    return _private_key, _public_key


@validate_call
def create_keys(
    asymmetric_keys_dir: str,
    key_size: int,
    private_key_fname: str,
    public_key_fname: str,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Create asymmetric keys and save them to files.

    Args:
        asymmetric_keys_dir (str     , required): Asymmetric keys directory.
        key_size            (int     , required): Asymmetric key size.
        private_key_fname   (str     , required): Asymmetric private key filename.
        public_key_fname    (str     , required): Asymmetric public key filename.
        warn_mode           (WarnEnum, optional): Warning mode. Defaults to WarnEnum.DEBUG.

    Raises:
        OSError: If failed to create asymmetric keys.
    """

    _private_key_path = os.path.join(asymmetric_keys_dir, private_key_fname)
    _public_key_path = os.path.join(asymmetric_keys_dir, public_key_fname)
    if os.path.isfile(_private_key_path) and os.path.isfile(_public_key_path):
        return

    _private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )
    _public_key = _private_key.public_key()

    _private_pem = _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    _public_pem = _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    utils.create_dir(create_dir=asymmetric_keys_dir, warn_mode=warn_mode)

    if not os.path.isfile(_private_key_path):
        try:
            with open(_private_key_path, "wb") as _private_key_file:
                _private_key_file.write(_private_pem)

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_private_key_path}' private key already exists!")
            else:
                logger.error(f"Failed to create '{_private_key_path}' private key!")
                raise

    if not os.path.isfile(_public_key_path):
        try:
            with open(_public_key_path, "wb") as _public_key_file:
                _public_key_file.write(_public_pem)

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_public_key_path}' public key already exists!")
            else:
                logger.error(f"Failed to create '{_public_key_path}' public key!")
                raise

    return


@validate_call
def get_private_key(
    private_key_path: str, as_str: bool = False
) -> Union[PrivateKeyTypes, str]:
    """Read asymmetric private key from file.

    Args:
        private_key_path (str , required): Asymmetric private key path.
        as_str           (bool, optional): Return private key as string. Defaults to False.

    Raises:
        FileNotFoundError: If asymmetric private key file not found.

    Returns:
        Union[PrivateKeyTypes, str]: Asymmetric private key as PrivateKeyTypes or str.
    """

    if not os.path.isfile(private_key_path):
        raise FileNotFoundError(f"Not found '{private_key_path}' private key!")

    _private_key: PrivateKeyTypes = None
    with open(private_key_path, "rb") as _private_key_file:
        _private_key_bytes: bytes = _private_key_file.read()
        _private_key: PrivateKeyTypes = serialization.load_pem_private_key(
            _private_key_bytes, password=None, backend=default_backend()
        )

    if as_str:
        _private_key = _private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    return _private_key


@validate_call
def get_public_key(
    public_key_path: str, as_str: bool = False
) -> Union[PublicKeyTypes, str]:
    """Read asymmetric public key from file.

    Args:
        public_key_path (str , required): Asymmetric public key path.
        as_str          (bool, optional): Return public key as string. Defaults to False.

    Raises:
        FileNotFoundError: If asymmetric public key file not found.

    Returns:
        Union[PublicKeyTypes, str]: Asymmetric public key as PublicKeyTypes or str.
    """

    if not os.path.isfile(public_key_path):
        raise FileNotFoundError(f"Not found '{public_key_path}' public key!")

    _public_key: PublicKeyTypes = None
    with open(public_key_path, "rb") as _public_key_file:
        _public_key_bytes: bytes = _public_key_file.read()
        _public_key: PublicKeyTypes = serialization.load_pem_public_key(
            _public_key_bytes, backend=default_backend()
        )

    if as_str:
        _public_key = _public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    return _public_key


@validate_call
def get_keys(
    private_key_path: str, public_key_path: str, as_str: bool = False
) -> Tuple[Union[PrivateKeyTypes, str], Union[PublicKeyTypes, str]]:
    """Read asymmetric keys from file.

    Args:
        private_key_path (str , required): Asymmetric private key path.
        public_key_path  (str , required): Asymmetric public key path.
        as_str           (bool, optional): Return keys as strings. Defaults to False.

    Returns:
        Tuple[Union[PrivateKeyTypes, str], Union[PublicKeyTypes, str]]: Private and public keys.
    """

    _private_key = get_private_key(private_key_path=private_key_path, as_str=as_str)
    _public_key = get_public_key(public_key_path=public_key_path, as_str=as_str)

    return _private_key, _public_key


@validate_call(config={"arbitrary_types_allowed": True})
def encrypt_with_public_key(
    plaintext: Union[str, bytes],
    public_key: PublicKeyTypes,
    base64_encode: bool = False,
    as_str: bool = False,
) -> Union[str, bytes]:
    """Encrypt plaintext with public key.

    Args:
        plaintext      (Union[str, bytes], required): Plaintext to encrypt.
        public_key     (PublicKeyTypes   , required): Public key.
        base64_encode  (bool             , optional): Encode ciphertext with base64. Defaults to False.
        as_str         (bool             , optional): Return ciphertext as string or bytes. Defaults to False.

    Raises:
        Exception: If failed to encrypt plaintext with asymmetric public key.

    Returns:
        Union[str, bytes]: Encrypted ciphertext as string or bytes.
    """

    if isinstance(plaintext, str):
        plaintext = plaintext.encode()

    _ciphertext: Union[str, bytes]
    try:
        logger.debug("Encrypting plaintext with asymmetric public key...")
        _ciphertext: bytes = public_key.encrypt(
            plaintext=plaintext,
            padding=padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        logger.debug("Successfully encrypted plaintext with asymmetric public key.")
    except Exception:
        logger.debug("Failed to encrypt plaintext with asymmetric public key!")
        raise

    if base64_encode:
        _ciphertext = base64.b64encode(_ciphertext)

    if as_str:
        _ciphertext = _ciphertext.decode()

    return _ciphertext


@validate_call(config={"arbitrary_types_allowed": True})
def decrypt_with_private_key(
    ciphertext: Union[str, bytes],
    private_key: PrivateKeyTypes,
    base64_decode: bool = False,
    as_str: bool = False,
) -> Union[str, bytes]:
    """Decrypt ciphertext with private key.

    Args:
        ciphertext    (Union[str, bytes], required): Ciphertext to decrypt.
        private_key   (PrivateKeyTypes  , required): Private key.
        base64_decode (bool             , optional): Decode ciphertext with base64. Defaults to False.
        as_str        (bool             , optional): Return plaintext as string or bytes. Defaults to False.

    Raises:
        Exception: If failed to decrypt ciphertext with asymmetric private key for any reason.

    Returns:
        Union[str, bytes]: Decrypted plaintext as string or bytes.
    """

    if isinstance(ciphertext, str):
        ciphertext = ciphertext.encode()

    if base64_decode:
        ciphertext = base64.b64decode(ciphertext)

    _plaintext: Union[str, bytes]
    try:
        logger.debug("Decrypting ciphertext with asymmetric private key...")
        _plaintext: bytes = private_key.decrypt(
            ciphertext=ciphertext,
            padding=padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        logger.debug("Successfully decrypted ciphertext with asymmetric private key.")
    except Exception:
        logger.debug("Failed to decrypt ciphertext with asymmetric private key!")
        raise

    if as_str:
        _plaintext = _plaintext.decode()

    return _plaintext


__all__ = [
    "async_create_keys",
    "async_get_private_key",
    "async_get_public_key",
    "async_get_keys",
    "create_keys",
    "get_private_key",
    "get_public_key",
    "get_keys",
    "encrypt_with_public_key",
    "decrypt_with_private_key",
]
