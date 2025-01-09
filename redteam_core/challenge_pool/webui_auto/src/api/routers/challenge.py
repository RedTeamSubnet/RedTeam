# -*- coding: utf-8 -*-

import os
import json
import base64
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

try:
    from modules.rt_wc_score import MetricsProcessor  # type: ignore
except ImportError:
    from rt_wc_score import MetricsProcessor  # type: ignore

from api import utils
from api.config import config
from api.helpers.crypto import asymmetric as asymmetric_helper
from api.helpers.crypto import symmetric as symmetric_helper
from api.schemas.data_types import MinerInput, MinerOutput
from api.logger import logger


router = APIRouter(tags=["Challenge"])
_templates = Jinja2Templates(directory="./templates")


@router.get(
    "/task",
    summary="Get task",
    description="This endpoint returns the webpage URL for the challenge.",
    response_model=MinerInput,
)
async def get_task():
    _miner_input = MinerInput(web_url=config.web.url)
    return _miner_input


@router.get(
    "/web",
    summary="Serves the webpage",
    description="This endpoint serves the webpage for the challenge.",
    response_class=HTMLResponse,
)
async def get_web(request: Request):

    ## Get the public key
    _public_key_path = os.path.join(
        config.api.paths.asymmetric_keys_dir,
        config.api.security.asymmetric.public_key_fname,
    )
    _public_key: str = await asymmetric_helper.async_get_public_key(
        public_key_path=_public_key_path, as_str=True
    )

    _id = utils.gen_unique_id()
    _nonce = utils.gen_random_string(length=32)

    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_id": _id,
            "public_key": _public_key,
            "nonce": _nonce,
        },
    )
    return _html_response


# @router.post(
#     "/decrypt",
#     summary="Decrypts the encrypted data",
#     description="This endpoint decrypts the encrypted data.",
# )
async def post_decrypt(miner_output: MinerOutput) -> str:

    ## 1. Get the private key
    _private_key_path = os.path.join(
        config.api.paths.asymmetric_keys_dir,
        config.api.security.asymmetric.private_key_fname,
    )
    _private_key: PrivateKeyTypes = await asymmetric_helper.async_get_private_key(
        private_key_path=_private_key_path
    )

    ## 2. Decrypt the symmetric key
    _key_bytes: bytes = asymmetric_helper.decrypt_with_private_key(
        ciphertext=miner_output.key,
        private_key=_private_key,
        base64_decode=True,
    )

    ## 3. Decrypt the ciphertext
    _iv_bytes: bytes = base64.b64decode(miner_output.iv)
    _plaintext: str = symmetric_helper.decrypt_aes_cbc(
        ciphertext=miner_output.ciphertext,
        key=_key_bytes,
        iv=_iv_bytes,
        base64_decode=True,
        as_str=True,
    )

    return _plaintext


@router.post(
    "/score",
    summary="Evaluate the challenge",
    description="This endpoint evaluates the challenge.",
)
async def post_score(miner_input: MinerInput, miner_output: MinerOutput):

    _score = 0.0
    _plaintext_miner_output = ""
    try:
        _plaintext_miner_output = await post_decrypt(miner_output=miner_output)
    except Exception as e:
        logger.error(f"Error in decrypting: {str(e)}")
        return _score

    _data = {}
    try:
        _data = json.loads(_plaintext_miner_output.strip())
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return _score

    try:
        _processor = MetricsProcessor()
        _result_dict: Dict[str, Any] = _processor(raw_data=_data)
        if _result_dict["analysis"]["score"]:
            _score = _result_dict["analysis"]["score"]
    except Exception as e:
        logger.error(f"Error in processing: {str(e)}")
        return _score

    return _score


__all__ = ["router"]
