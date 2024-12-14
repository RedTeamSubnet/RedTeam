# -*- coding: utf-8 -*-

import base64
from typing import Union

from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from pydantic import validate_call
from beans_logging import logger


@validate_call(config={"arbitrary_types_allowed": True})
def decrypt_aes_cbc(
    ciphertext: Union[str, bytes],
    key: bytes,
    iv: bytes,
    base64_decode: bool = False,
    as_str: bool = False,
) -> Union[str, bytes]:
    """Decrypts a ciphertext using AES-CBC key and iv.

    Args:
        ciphertext    (Union[str, bytes], required): The ciphertext to decrypt.
        key           (bytes            , required): The key to use for decryption.
        iv            (bytes            , required): The initialization vector to use for decryption.
        base64_decode (bool             , optional): Whether to decode the ciphertext from base64. Defaults to False.
        as_str        (bool             , optional): Whether to return the plaintext as a string or bytes. Defaults to False.

    Raises:
        Exception: If failed to decrypt ciphertext using AES-CBC key and iv for any reason.

    Returns:
        Union[str, bytes]: The decrypted plaintext as a string or bytes.
    """

    if isinstance(ciphertext, str):
        ciphertext = ciphertext.encode()

    if base64_decode:
        ciphertext = base64.b64decode(ciphertext)

    _plaintext: Union[str, bytes]
    try:
        logger.debug("Decrypting ciphertext using AES-CBC key and iv...")
        _cipher = ciphers.Cipher(algorithms.AES(key), modes.CBC(iv))
        _decryptor = _cipher.decryptor()
        _plaintext = _decryptor.update(ciphertext) + _decryptor.finalize()
        logger.debug("Successfully decrypted ciphertext using AES-CBC key and iv.")
    except Exception:
        logger.debug("Failed to decrypt ciphertext using AES-CBC key and iv!")
        raise

    if as_str:
        _plaintext = _plaintext.decode()

    return _plaintext


__all__ = [
    "decrypt_aes_cbc",
]
