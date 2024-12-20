import datetime
import numpy as np
import pandas as pd

from typing import List, Dict, Optional, Union
from pydantic import BaseModel
from cryptography.fernet import Fernet
from ..constants import constants


class MinerCommit(BaseModel):
    encrypted_commit: str
    timestamp: float
    docker_hub_id: Optional[str] = None
    key: Optional[str] = None

    def update(self, **kwargs) -> None:
        """
        Update the MinerCommit with new key if provided.
        """
        self.key = kwargs.get("key", self.key)

    def reveal(self) -> bool:
        """
        Decrypts the encrypted commit to reveal the docker_hub_id.
        Requires a valid encryption key to be set.
        Returns True if successful, False otherwise.
        """
        if not self.key:
            return False
        try:
            f = Fernet(self.key)
            decrypted_data = f.decrypt(self.encrypted_commit).decode()
            self.docker_hub_id = decrypted_data.split("---")[1]
            return True
        except Exception as e:
            # Consider logging the error
            return False


class ChallengeRecord(BaseModel):
    point: float = 0
    score: float = 0
    date: str = datetime.datetime.now().strftime("%Y-%m-%d")
    docker_hub_id: Optional[str] = None
    uid: Optional[int] = None


class ScoringLog(BaseModel):
    uid: int
    score: float
    miner_input: dict
    miner_output: Union[dict, None]
    miner_docker_image: str


class MinerManager:
    def __init__(self, challenge_name: str, challenge_incentive_weight: float):
        """
        Initializes the MinerManager to track scores and challenges.
        """
        self.challenge_name = challenge_name
        self.uids_to_commits: Dict[int, MinerCommit] = {}
        self.challenge_records: Dict[str, ChallengeRecord] = {}
        self.challenge_incentive_weight = challenge_incentive_weight
    
    def update_uid_to_commit(self, uids: List[int], commits: List[MinerCommit]) -> None:
        for uid, commit in zip(uids, commits):
            self.uids_to_commits[uid] = commit  

    def update_scores(self, logs: List[ScoringLog]) -> None:
        """
        Updates the scores for miners based on new logs.
        Ensures daily records are maintained.
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if today in self.challenge_records:
            # No need to update if today's record already exists
            return

        prev_day = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        prev_day_record = self.challenge_records.get(prev_day)

        if prev_day_record is None:
            prev_day_record = (
                ChallengeRecord()
            )  # Default record for the previous day if not found

        logs_df = pd.DataFrame([log.model_dump() for log in logs])

        # Group by uid and mean the scores
        scores = logs_df.groupby("uid")["score"].mean().sort_values(ascending=False)

        best_uid = scores.index[0]
        best_score = scores.iloc[0]

        if best_score > prev_day_record.score:
            point = max(best_score - prev_day_record.score, 0) * 100
            today_record = ChallengeRecord(
                score=best_score,
                date=today,
                docker_hub_id=self.uids_to_commits.get(
                    best_uid
                ),
                point=point,
                uid=best_uid,
            )
            self.challenge_records[today] = today_record
        else:
            # Handle if no score improvement
            self.challenge_records[today] = ChallengeRecord(
                score=prev_day_record.score, date=today
            )

    def get_onchain_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores, applying decay for older records.
        """
        scores = np.zeros(n_uids)  # Should this be configurable?
        today = datetime.datetime.now()

        for date_str, record in self.challenge_records.items():
            record_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            days_passed = (today - record_date).days
            point = constants.decay_points(record.point, days_passed)
            if record.uid is not None:
                scores[record.uid] += point

        return scores
