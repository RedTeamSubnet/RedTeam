from typing import Dict

from pydantic import BaseModel


class MinerInput(BaseModel):
    html_content: str

class MinerOutput(BaseModel):
    ui_metrics: Dict