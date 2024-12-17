# -*- coding: utf-8 -*-

import os
import errno
from datetime import timedelta

from pydantic import validate_call
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from beans_logging import logger

from api.constants import WarnEnum
from api import utils


@validate_call
def generate_ssl_certs(
    ssl_dir: str,
    cert_fname: str,
    key_fname: str,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:
    """Generate ssl key and cert files.

    Args:
        ssl_dir    (str     , required): SSL directory path.
        cert_fname (str     , required): Certificate file name.
        key_fname  (str     , required): Key file name.
        warn_mode  (WarnEnum, optional): Warning mode. Defaults to WarnEnum.DEBUG.

    Raises:
        OSError: If failed to create key or cert files.
    """

    _key_path = os.path.join(ssl_dir, key_fname)
    _cert_path = os.path.join(ssl_dir, cert_fname)
    if os.path.isfile(_key_path) and os.path.isfile(_cert_path):
        return

    logger.debug(
        f"Generating ssl key and cert files: ['{_key_path}', '{_cert_path}']..."
    )

    _private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    _subject = _issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Seoul"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Seoul"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )
    _cert = (
        x509.CertificateBuilder()
        .subject_name(_subject)
        .issuer_name(_issuer)
        .public_key(_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(utils.now_utc_dt())
        .not_valid_after(utils.now_utc_dt() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
        )
        .sign(_private_key, hashes.SHA256())
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
                logger.debug(f"'{_key_path}' ssl key file already exists!")
            else:
                logger.error(f"Failed to create '{_key_path}' ssl key file!")
                raise

    if not os.path.isfile(_cert_path):
        try:
            with open(_cert_path, "wb") as _cert_file:
                _cert_file.write(_cert.public_bytes(serialization.Encoding.PEM))

        except OSError as err:
            if (err.errno == errno.EEXIST) and (warn_mode == WarnEnum.DEBUG):
                logger.debug(f"'{_cert_path}' ssl cert file already exists!")
            else:
                logger.error(f"Failed to create '{_cert_path}' ssl cert file!")
                raise

    logger.debug("Successfully generated ssl key and cert files.")


__all__ = [
    "generate_ssl_certs",
]
