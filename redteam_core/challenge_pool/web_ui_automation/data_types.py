from typing import Dict, Optional, List

from pydantic import BaseModel


class MinerInput(BaseModel):
    html_content: str
    is_validator: Optional[bool] = False

class MinerOutput(BaseModel):
    checkbox_states: List[bool]
    ui_metrics: Optional[Dict] = None