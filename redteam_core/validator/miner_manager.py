import datetime
from typing import Dict, List, Optional, Union

import bittensor as bt
import numpy as np
import pandas as pd
import requests
from cryptography.fernet import Fernet
from pydantic import BaseModel

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
    date: str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    scored_date: Optional[str] = None
    docker_hub_id: Optional[str] = None
    uid: Optional[int] = None


class ScoringLog(BaseModel):
    uid: int
    score: float
    miner_input: Optional[dict] = None
    miner_output: Optional[dict] = None
    miner_docker_image: str
    error: Optional[str] = None
    baseline_score: Optional[float] = None


class MinerManager:
    def __init__(self, challenge_name: str, challenge_incentive_weight: float, metagraph: bt.metagraph):
        """
        Initializes the MinerManager to track scores and challenges.
        """
        self.challenge_name = challenge_name
        self.uids_to_commits: Dict[int, MinerCommit] = {}
        self.challenge_records: Dict[str, ChallengeRecord] = {}
        self.challenge_incentive_weight = challenge_incentive_weight
        self.metagraph = metagraph

    def update_uid_to_commit(self, uids: List[int], commits: List[MinerCommit]) -> None:
        for uid, commit in zip(uids, commits):
            self.uids_to_commits[uid] = commit

    def update_scores(self, logs: List[ScoringLog]) -> None:
        """
        Updates the scores for miners based on new logs.
        Ensures daily records are maintained.
        """
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

        if today in self.challenge_records:
            # No need to update if today's record already exists
            return

        if len(logs) == 0:
            # No logs, so we raise an error
            raise ValueError(f"[MINER MANAGER] No logs provided, challenge {self.challenge_name} scores cannot be updated for {today}.")

        # Find the most recent record by looking through all past dates
        most_recent_record = None
        most_recent_date = None

        for date_str, record in self.challenge_records.items():
            if most_recent_date is None or date_str > most_recent_date:
                most_recent_date = date_str
                most_recent_record = record

        # If no record found, create a blank one (first day of scoring)
        if most_recent_record is None:
            most_recent_record = ChallengeRecord()

        logs_df = pd.DataFrame([log.model_dump() for log in logs])

        # Group by uid and mean the scores
        scores = logs_df.groupby("uid")["score"].mean().sort_values(ascending=False)

        best_uid = scores.index[0]
        best_score = scores.iloc[0]
        best_docker_hub_id = logs_df[logs_df["uid"] == best_uid]["miner_docker_image"].iloc[0]

        if best_score > most_recent_record.score:
            # Miner made improvement
            point = max(best_score - most_recent_record.score, 0) * 100
            today_record = ChallengeRecord(
                point=point,
                score=best_score,
                date=today,
                scored_date=today,
                docker_hub_id=best_docker_hub_id,
                uid=best_uid,
            )
            self.challenge_records[today] = today_record
        else:
            # Miner did not make improvement, so we use the decayed points from the previous day
            today_record = ChallengeRecord(
                score=most_recent_record.score,
                date=today,
                scored_date=most_recent_record.scored_date,
                docker_hub_id=most_recent_record.docker_hub_id,
                uid=most_recent_record.uid
            )
            self.challenge_records[today] = today_record

    def _get_challenge_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on challenge records (solution performance), applying decay for older records.
        """
        scores = np.zeros(n_uids)  # Should this be configurable?
        today = datetime.datetime.now(datetime.timezone.utc)

        total_points = 0
        for date_str, record in self.challenge_records.items():
            # Only add points for the records that have scored date equal to recorded date (recorded by making improvement)
            if record.scored_date == record.date:
                # Calculate decayed points
                record_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
                days_passed = (today - record_date).days
                point = constants.decay_points(record.point, days_passed)
                scores[record.uid] += point
                total_points += point

        if total_points > 0:
            scores /= total_points

        return scores
    def _get_newly_registration_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on newly registration, high for more recent registrations.
        Only considers UIDs registered within the immunity period (defined in blocks).
        Scores range from 1.0 (just registered) to 0.0 (older than immunity period).
        """
        scores = np.zeros(n_uids)
        current_time = datetime.datetime.now(datetime.timezone.utc)
        endpoint = constants.STORAGE_URL + "/fetch-uids-registration-time"

        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            uids_registration_time = response.json()["data"]

            # Process uids_registration_time to get the scores
            for uid, registration_time in uids_registration_time.items():
                uid = int(uid)
                if uid >= n_uids:
                    continue

                # Parse the UTC datetime string
                reg_time = datetime.datetime.strptime(
                    registration_time,
                    "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=datetime.timezone.utc)

                seconds_since_registration = (current_time - reg_time).total_seconds()
                blocks_since_registration = seconds_since_registration / 12

                # Only consider UIDs registered within immunity period
                if blocks_since_registration <= constants.SUBNET_IMMUNITY_PERIOD:
                    # Score decreases linearly from 1.0 (just registered) to 0.0 (immunity period ended)
                    scores[uid] = max(0, 1.0 - (blocks_since_registration / constants.SUBNET_IMMUNITY_PERIOD))

            # Normalize scores if any registrations exist
            if np.sum(scores) > 0:
                scores = scores / np.sum(scores)

        except Exception as e:
            bt.logging.error(f"Error fetching uids registration time: {e}")
            return np.zeros(n_uids)

        return scores

    def _get_alpha_stake_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on alpha stake, high for more stake.
        Uses square root transformation to reduce the impact of very high stakes, encourage small holders.
        """
        scores = np.zeros(n_uids)
        # Apply square root transformation to reduce the impact of high stakes
        sqrt_alpha_stakes = np.sqrt(self.metagraph.alpha_stake)
        total_sqrt_alpha_stakes = np.sum(sqrt_alpha_stakes)
        if total_sqrt_alpha_stakes > 0:
            # Normalize stakes to get scores between 0 and 1
            scores = sqrt_alpha_stakes / total_sqrt_alpha_stakes
        return scores

    def get_onchain_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of weighted scores combining:
        1. Challenge scores (based on performance improvements)
        2. Newly registration scores (favoring recently registered UIDs)
        3. Alpha stake scores (based on stake amount)

        Weights are defined in constants:
        - CHALLENGE_SCORES_WEIGHT (85%)
        - NEWLY_REGISTRATION_WEIGHT (10%)
        - ALPHA_STAKE_WEIGHT (5%)
        """
        # Get challenge performance scores
        challenge_scores = self._get_challenge_scores(n_uids)

        # Get newly registration scores
        registration_scores = self._get_newly_registration_scores(n_uids)

        # Get alpha stake scores
        alpha_stake_scores = self._get_alpha_stake_scores(n_uids)

        # Combine scores using weights from constants
        final_scores = (
            challenge_scores * constants.CHALLENGE_SCORES_WEIGHT +
            registration_scores * constants.NEWLY_REGISTRATION_WEIGHT +
            alpha_stake_scores * constants.ALPHA_STAKE_WEIGHT
        )

        return final_scores
