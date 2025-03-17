import hashlib
import json
import time
from typing import Union
from typing import Callable

import bittensor as bt
from pydantic import BaseModel

def create_validator_request_header_fn(
    validator_uid: int,
    validator_hotkey: str,
    keypair: bt.Keypair
) -> Callable[[Union[bytes, str, dict, BaseModel]], str]:
    """
    Creates a validator request header function.
    """

    def get_validator_request_header(body: Union[bytes, str, dict, BaseModel]) -> dict:
        """
        Creates a validator request header.
        Args:
            body (Union[bytes, str, dict, BaseModel]): The body of the request, can be a bytes, string, dictionary, or BaseModel, this is non hashed version
        Returns:
            dict: The validator request header.
        """
        timestamp = str(time.time_ns())
        if isinstance(body, bytes):
            body_hash = hashlib.sha256(body).hexdigest()
        elif isinstance(body, str):
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        elif isinstance(body, dict):
            body_hash = hashlib.sha256(json.dumps(body).encode("utf-8")).hexdigest()
        elif isinstance(body, BaseModel):
            body_hash = hashlib.sha256(body.model_dump_json().encode("utf-8")).hexdigest()

        signature = "0x" + keypair.sign(f"{body_hash}.{timestamp}").hex()

        header = {
            "validator-uid": str(validator_uid),
            "validator-hotkey": validator_hotkey,
            "timestamp": timestamp,
            "signature": signature,
        }
        return header

    return get_validator_request_header
