from pydantic import BaseModel
from cryptography.fernet import Fernet
import datetime
import numpy as np
import pandas as pd

class MinerCommit(BaseModel):
    encrypted_commit: str
    timestamp: float
    docker_hub_id: str = None
    key: str = None
    
    def update(self, **kwargs):
        self.key = kwargs.get("key", self.key)

    def reveal(self) -> bool:
        if self.key:
            f = Fernet(self.key)
            self.docker_hub_id = f.decrypt(self.encrypted_commit).decode().split("---")[1]
            return True
        return False

class ChallengeRecord(BaseModel):
    point: float = 0
    score: float = 0
    date: str = datetime.datetime.now().strftime("%Y-%m-%d")
    docker_hub_id: str = None
    uid: int = None


class MinerManager(BaseModel):
    def __init__(self, challenge_name: str):
        self.challenge_name = challenge_name
        self.uids_to_commits = {}
        self.challenge_records: dict[str, ChallengeRecord] = {}
        self.points = np.zeros(256)

    def update_scores(self, logs: list):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if today in self.challenge_records:
            return
        prev_day = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        prev_day_record = self.challenge_records.get(prev_day, None)

        logs = pd.DataFrame(logs)
        # Group by uid and sum the scores
        scores = logs.groupby("uid")["score"].sum()
        sorted_scores = scores.sort_values(ascending=False)
        best_score = sorted_scores.iloc[0]
        best_uid = sorted_scores.index[0]
        if best_score > prev_day_record.score:
            score_diff = best_score - prev_day_record.score
            today_record = ChallengeRecord(score=best_score, date=today, docker_hub_id=self.uids_to_commits[best_uid].docker_hub_id, point=score_diff, uid=best_uid)
