from pydantic import BaseModel, field_validator
from typing import List


class MinerInput(BaseModel):
    """
    Represents the input data for the challenge.
    Includes a prompt, a list of responses to evaluate, 
    and the ground truth ranking for those responses.
    """
    prompt: str
    responses: List[str]
    groundtruth_ranking: List[int]  # Ranking of responses based on ground truth, higher is better, hidden from miner for evaluation purposes

    
class MinerOutput(BaseModel):
    """
    Represents the miner's output for the challenge.
    Contains the quality scores assigned to the responses.
    """
    response_quality: List[float]  # Quality scores for each response in MinerInput, higher indicates better quality
