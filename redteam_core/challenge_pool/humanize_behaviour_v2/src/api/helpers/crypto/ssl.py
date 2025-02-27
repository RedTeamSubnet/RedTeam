# -*- coding: utf-8 -*-

import os
import errno
from datetime import timedelta
from typing import Union

import aiofiles
import aiofiles.os
from pydantic import validate_call, BaseModel, Field
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from beans_logging import logger

from api.core.constants import WarnEnum
from api.core import utils

from . import asymmetric as asymmetric_helper


class X509AttrsPM(BaseModel):
    C: str = Field(default="US", min_length=2, max_length=2)
    ST: str = Field(default="Washington", min_length=2, max_length=256)
    L: str = Field(default="Seattle", min_length=2, max_length=256)
    O: str = Field(default="Organization", min_length=2, max_length=256)
    OU: str = Field(default="Organization Unit", min_length=2, max_length=256)
    CN: str = Field(default="localhost", min_length=2, max_length=256)
    DNS: str = Field(default="localhost", min_length=2, max_length=256)


@validate_call
async def async_create_ssl_certs(
    ssl_dir: str,
    cert_fname: str,
    key_fname: str,
    key_size: int,
    x509_attrs: X509AttrsPM = X509AttrsPM(),
    force: bool = False,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Async generate and create SSL key and cert files.

    Args:
        ssl_dir    (str            , required): SSL directory path.
        cert_fname (str            , required): Certificate file name.
        key_fname  (str            , required): Key file name.
        key_size   (int            , required): Key size.
        x509_attrs (X509AttrsPM, optional): X509 named attributes. Defaults to X509AttrsPM().
        force      (bool           , optional): Force to create SSL key and cert files. Defaults to False.
        warn_mode  (WarnEnum       , optional): Warning mode. Defaults to WarnEnum.DEBUG.

    Raises:
        FileExistsError: When warning mode is set to ERROR and SSL key or cert files already exist.
        OSError        : If failed to create SSL key or cert files.
    """

    _key_path = os.path.join(ssl_dir, key_fname)
    _cert_path = os.path.join(ssl_dir, cert_fname)

    if force:
        await utils.async_remove_file(file_path=_key_path, warn_mode=warn_mode)
        await utils.async_remove_file(file_path=_cert_path, warn_mode=warn_mode)

    if (await aiofiles.os.path.isfile(_key_path)) and (
        await aiofiles.os.path.isfile(_cert_path)
    ):
        logger.trace(
            f"SSL key and cert files already exist: ['{_key_path}', '{_cert_path}']"
        )
        return

    _meesage = f"Generating SSL key and cert files: ['{_key_path}', '{_cert_path}']..."
    if warn_mode == WarnEnum.ALWAYS:
        logger.info(_meesage)
    elif warn_mode == WarnEnum.DEBUG:
        logger.debug(_meesage)

    _private_key: Union[RSAPrivateKey, PrivateKeyTypes]
    if await aiofiles.os.path.isfile(_key_path):
        if warn_mode == WarnEnum.ERROR:
            raise FileExistsError(f"'{_key_path}' SSL key file already exists!")

        _private_key: PrivateKeyTypes = await asymmetric_helper.async_get_private_key(
            private_key_path=_key_path
        )
    else:
        _private_key: RSAPrivateKey = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size
        )

    if await aiofiles.os.path.isfile(_cert_path):
        if warn_mode == WarnEnum.ERROR:
            raise FileExistsError(f"'{_cert_path}' SSL cert file already exists!")

        await utils.async_remove_file(file_path=_cert_path, warn_mode=warn_mode)

    _subject = _issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, x509_attrs.C),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, x509_attrs.ST),
            x509.NameAttribute(NameOID.LOCALITY_NAME, x509_attrs.L),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, x509_attrs.O),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, x509_attrs.OU),
            x509.NameAttribute(NameOID.COMMON_NAME, x509_attrs.CN),
        ]
    )
    _cert = (
        x509.CertificateBuilder()
        .subject_name(name=_subject)
        .issuer_name(name=_issuer)
        .public_key(key=_private_key.public_key())
        .serial_number(number=x509.random_serial_number())
        .not_valid_before(time=utils.now_utc_dt())
        .not_valid_after(time=utils.now_utc_dt() + timedelta(days=365))
        .add_extension(
            extval=x509.SubjectAlternativeName([x509.DNSName(x509_attrs.DNS)]),
            critical=False,
        )
        .sign(private_key=_private_key, algorithm=hashes.SHA256())
    )

    await utils.async_create_dir(create_dir=ssl_dir, warn_mode=warn_mode)

    if not await aiofiles.os.path.isfile(_key_path):
        try:
            async with aiofiles.open(_key_path, "wb") as _key_file:
                await _key_file.write(
                    _private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_key_path}' SSL key file already exists!")
            else:
                logger.error(f"Failed to create '{_key_path}' SSL key file!")
                raise

    if not await aiofiles.os.path.isfile(_cert_path):
        try:
            async with aiofiles.open(_cert_path, "wb") as _cert_file:
                await _cert_file.write(_cert.public_bytes(serialization.Encoding.PEM))

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_cert_path}' SSL cert file already exists!")
            else:
                logger.error(f"Failed to create '{_cert_path}' SSL cert file!")
                raise

    _message = f"Successfully generated SSL key and cert files: ['{_key_path}', '{_cert_path}']"
    if warn_mode == WarnEnum.ALWAYS:
        logger.success(_message)
    elif warn_mode == WarnEnum.DEBUG:
        logger.debug(_message)

    return


@validate_call
def create_ssl_certs(
    ssl_dir: str,
    key_fname: str,
    cert_fname: str,
    key_size: int,
    x509_attrs: X509AttrsPM = X509AttrsPM(),
    force: bool = False,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Generate and create SSL key and cert files.

    Args:
        ssl_dir    (str            , required): SSL directory path.
        key_fname  (str            , required): Key file name.
        cert_fname (str            , required): Certificate file name.
        key_size   (int            , required): Key size.
        x509_attrs (X509AttrsPM, optional): X509 named attributes. Defaults to X509AttrsPM().
        force      (bool           , optional): Force to create SSL key and cert files. Defaults to False.
        warn_mode  (WarnEnum       , optional): Warning mode. Defaults to WarnEnum.DEBUG.

    Raises:
        FileExistsError: When warning mode is set to ERROR and SSL key or cert files already exist.
        OSError        : If failed to create SSL key or cert files.
    """

    _key_path = os.path.join(ssl_dir, key_fname)
    _cert_path = os.path.join(ssl_dir, cert_fname)

    if force:
        utils.remove_file(file_path=_key_path, warn_mode=warn_mode)
        utils.remove_file(file_path=_cert_path, warn_mode=warn_mode)

    if os.path.isfile(_key_path) and os.path.isfile(_cert_path):
        logger.trace(
            f"SSL key and cert files already exist: ['{_key_path}', '{_cert_path}']"
        )
        return

    _message = f"Generating SSL key and cert files: ['{_key_path}', '{_cert_path}']..."
    if warn_mode == WarnEnum.ALWAYS:
        logger.info(_message)
    elif warn_mode == WarnEnum.DEBUG:
        logger.debug(_message)

    _private_key: Union[RSAPrivateKey, PrivateKeyTypes]
    if os.path.isfile(_key_path):
        if warn_mode == WarnEnum.ERROR:
            raise FileExistsError(f"'{_key_path}' SSL key file already exists!")

        _private_key: PrivateKeyTypes = asymmetric_helper.get_private_key(
            private_key_path=_key_path
        )
    else:
        _private_key: RSAPrivateKey = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size
        )

    if os.path.isfile(_cert_path):
        if warn_mode == WarnEnum.ERROR:
            raise FileExistsError(f"'{_cert_path}' SSL cert file already exists!")

        utils.remove_file(file_path=_cert_path, warn_mode=warn_mode)

    _subject = _issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, x509_attrs.C),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, x509_attrs.ST),
            x509.NameAttribute(NameOID.LOCALITY_NAME, x509_attrs.L),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, x509_attrs.O),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, x509_attrs.OU),
            x509.NameAttribute(NameOID.COMMON_NAME, x509_attrs.CN),
        ]
    )
    _cert = (
        x509.CertificateBuilder()
        .subject_name(name=_subject)
        .issuer_name(name=_issuer)
        .public_key(key=_private_key.public_key())
        .serial_number(number=x509.random_serial_number())
        .not_valid_before(time=utils.now_utc_dt())
        .not_valid_after(time=utils.now_utc_dt() + timedelta(days=365))
        .add_extension(
            extval=x509.SubjectAlternativeName([x509.DNSName(x509_attrs.DNS)]),
            critical=False,
        )
        .sign(private_key=_private_key, algorithm=hashes.SHA256())
    )

    utils.create_dir(create_dir=ssl_dir, warn_mode=warn_mode)

    if not os.path.isfile(_key_path):
        try:
            with open(_key_path, "wb") as _key_file:
                _key_file.write(
                    _private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_key_path}' SSL key file already exists!")
            else:
                logger.error(f"Failed to create '{_key_path}' SSL key file!")
                raise

    if not os.path.isfile(_cert_path):
        try:
            with open(_cert_path, "wb") as _cert_file:
                _cert_file.write(_cert.public_bytes(serialization.Encoding.PEM))

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_cert_path}' SSL cert file already exists!")
            else:
                logger.error(f"Failed to create '{_cert_path}' SSL cert file!")
                raise

    _message = f"Successfully generated SSL key and cert files: ['{_key_path}', '{_cert_path}']"
    if warn_mode == WarnEnum.ALWAYS:
        logger.success(_message)
    elif warn_mode == WarnEnum.DEBUG:
        logger.debug(_message)

    return


__all__ = [
    "async_create_ssl_certs",
    "create_ssl_certs",
]
