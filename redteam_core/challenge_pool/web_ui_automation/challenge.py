import os
from typing import Dict

from .data_types import MinerInput, MinerOutput

class Challenge:
    """
    User Interface Automation Detection Challenge
    Validates genuine human UI interactions vs automated scripts
    """
    def __init__(self):
        self.base_path = os.path.join(os.path.dirname(__file__), 'static', 'html')
        
    def _load_html(self, filename: str) -> str:
        with open(os.path.join(self.base_path, filename), 'r') as f:
            return f.read()

    def prepare_task(self) -> MinerInput:
        html_path = "./templates/index.html"
        html_content = self._load_html(html_path)
        return MinerInput(html_content=html_content)

    def score_task(self, miner_output: MinerOutput) -> float:
        checkbox_states = miner_output.ui_metrics.get('checkbox_states', [])
        base_score = 1.0 if all(checkbox_states) else 0.0
        return self._calculate_score(base_score, miner_output.ui_metrics)

    def _calculate_score(self, base_score: float, metrics: Dict) -> float:
        score = base_score
        movements = metrics.get('movements', [])
        clicks = metrics.get('clicks', [])
        
        if len(movements) < 10:
            score *= 0.5
        if len(clicks) < 3:
            score *= 0.7
            
        return score