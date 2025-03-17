# -*- coding: utf-8 -*-

from pydantic import BaseModel, HttpUrl, Field
from fastapi import Body

from api.config import config
from api.schemas import BasePM


class MinerInput(BasePM):
    web_url: HttpUrl = Field(
        default=config.web.url,
        title="Web URL",
        description="Webpage URL for the challenge.",
        examples=["http://localhost:8000"],
    )


class MinerOutput(BaseModel):
    ciphertext: str = Body(
        ...,
        min_length=2,
        title="Ciphertext",
        description="The ciphertext.",
        examples=["rp7RivGGTyZLXVlQi29bhWMciRkBt8yQ"],
    )
    key: str = Body(
        ...,
        min_length=2,
        title="Key",
        description="The random key.",
        examples=["QiywqDkyhLiF6vx2I1ag8j4qTqozyO3t"],
    )
    iv: str = Body(
        ...,
        min_length=2,
        title="IV",
        description="The initialization vector.",
        examples=["wvpQOM3ZOukq3LUPJX3fjNnzyjtkhsWZ"],
    )


__all__ = [
    "MinerInput",
    "MinerOutput",
]
