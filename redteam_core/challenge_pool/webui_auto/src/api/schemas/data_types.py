# -*- coding: utf-8 -*-

from typing import Dict, Any

from pydantic import BaseModel, HttpUrl, Field

from api.config import config
from api.schemas import BasePM


class TaskPM(BasePM):
    web_url: HttpUrl = Field(
        default=config.web.url,
        title="Web URL",
        description="Webpage URL for the challenge.",
        examples=[config.web.url],
    )


class MinerInput(BaseModel):
    html_content: str


class MinerOutput(BaseModel):
    ui_metrics: Dict[Any, Any]


__all__ = [
    "TaskPM",
    "MinerInput",
    "MinerOutput",
]
