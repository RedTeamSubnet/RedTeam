# -*- coding: utf-8 -*-

from typing import Dict, Any

from pydantic import BaseModel


class MinerInput(BaseModel):
    html_content: str


class MinerOutput(BaseModel):
    ui_metrics: Dict[Any, Any]


__all__ = [
    "HealthPM",
    "MinerInput",
    "MinerOutput",
]
