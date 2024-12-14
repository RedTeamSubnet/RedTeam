from cryptography.exceptions import (
    UnsupportedAlgorithm,
    AlreadyFinalized,
    InvalidSignature,
    NotYetFinalized,
    AlreadyUpdated,
    InvalidKey,
    InvalidTag,
)
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
import base64
import json
from typing import Tuple, Any

from api.logger import logger
from api.helpers.crypto.asymmetric import decrypt_with_private_key


class DecryptPayload:
    def __init__(self, private_key: RSAPrivateKey):
        self._private_key = private_key

    def decrypt(self, encrypted_payload: str) -> Any:
        encrypted_aes_key, encrypted_iv, encrypted_data = self._parse_payload(
            encrypted_payload
        )
        aes_key = self._decrypt_with_private_key(encrypted_aes_key)
        iv = self._decrypt_with_private_key(encrypted_iv)
        decrypted_data = self._decrypt_aes(encrypted_data, aes_key, iv)
        return json.loads(decrypted_data)

    def _parse_payload(self, payload: str) -> Tuple[bytes, bytes, bytes]:
        # logger.debug(f"Decrypting payload: {payload}")
        parts = payload.split("::")
        # parts = base64.b64decode(payload).decode().split('::')
        # logger.info(f"Payload parts: {parts}")

        return (
            base64.b64decode(parts[0].encode()),
            base64.b64decode(parts[1].encode()),
            bytes.fromhex(parts[2]),
        )

    def _decrypt_with_private_key(self, encrypted_data: bytes) -> bytes:
        plain_text = b""
        try:
            plain_text = self._private_key.decrypt(
                encrypted_data,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except UnsupportedAlgorithm:
            logger.error("Unsupported algorithm for decryption")
        except AlreadyFinalized:
            logger.error("Decryptor is already finalized")
        except InvalidSignature:
            logger.error("Invalid signature for decryption")
        except NotYetFinalized:
            logger.error("Decryptor is not yet finalized")
        except AlreadyUpdated:
            logger.error("Decryptor is already updated")
        except InvalidKey:
            logger.error("Invalid key for decryption")
        except InvalidTag:
            logger.error("Invalid tag for decryption")
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            logger.error(f"Type of error: {type(e)}")
        return plain_text

    def _decrypt_aes(self, encrypted_data: bytes, key: bytes, iv: bytes) -> str:

        cipher = Cipher(algorithms.AES256(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode("utf-8")
