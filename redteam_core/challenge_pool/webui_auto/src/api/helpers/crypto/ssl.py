# -*- coding: utf-8 -*-

import os
from datetime import timedelta

from pydantic import validate_call
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from api.constants import WarnEnum
from api import utils


@validate_call
def generate_ssl_certs(
    ssl_dir: str,
    cert_fname: str,
    key_fname: str,
    warn_mode: WarnEnum = WarnEnum.DEBUG,
) -> None:

    _key_path = os.path.join(ssl_dir, key_fname)
    _cert_path = os.path.join(ssl_dir, cert_fname)
    if os.path.isfile(_key_path) and os.path.isfile(_cert_path):
        return

    # Generate private key
    _private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    utils.create_dir(create_dir=ssl_dir, warn_mode=warn_mode)

    # Write private key to file
    with open(_key_path, "wb") as _file:
        _file.write(
            _private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Create a self-signed certificate
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

    with open(_cert_path, "wb") as _cert_file:
        _cert_file.write(_cert.public_bytes(serialization.Encoding.PEM))


__all__ = [
    "generate_ssl_certs",
]
