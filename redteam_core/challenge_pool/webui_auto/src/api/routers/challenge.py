# -*- coding: utf-8 -*-

import os
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PublicKeyTypes

try:
    from api.modules.rt_wc_score import MetricsProcessor  # type: ignore
except ImportError:
    from rt_wc_score import MetricsProcessor  # type: ignore

from api import utils
from api.config import config
from api.helpers.crypto import asymmetric_keys as asymmetric_keys_helper
from api.schemas.data_types import MinerInput, MinerOutput


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

    _public_key_path = os.path.join(
        config.api.paths.asymmetric_keys_dir,
        config.api.security.asymmetric_keys.public_key_fname,
    )
    _public_key: PublicKeyTypes = await asymmetric_keys_helper.async_get_public_key(
        public_key_path=_public_key_path
    )

    _public_key_str = _public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    _id = utils.gen_unique_id()
    _nonce = utils.gen_random_string(length=32)

    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_id": _id,
            "public_key": _public_key_str,
            "nonce": _nonce,
        },
    )
    return _html_response


@router.post(
    "/score",
    summary="Evaluate the challenge",
    description="This endpoint evaluates the challenge.",
)
async def post_score(miner_input: MinerInput, miner_output: MinerOutput):
    _processor = MetricsProcessor()
    _result_dict: Dict[str, Any] = _processor(raw_data=miner_output.model_dump())

    _score = 0.0
    if _result_dict["success"] is True:
        _score = 1.0

    return _score


__all__ = ["router"]
