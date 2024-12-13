# -*- coding: utf-8 -*-

from typing import Dict, Any

from pydantic import BaseModel, HttpUrl, Field

from api.config import config
from api.schemas import BasePM


class MinerInput(BasePM):
    web_url: HttpUrl = Field(
        default=config.web.url,
        title="Web URL",
        description="Webpage URL for the challenge.",
        examples=[config.web.url],
    )


class MinerOutput(BaseModel):
    data: Dict[Any, Any]
    key: str


__all__ = [
    "MinerInput",
    "MinerOutput",
]
