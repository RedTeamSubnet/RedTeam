import pytest

from datetime import datetime, timedelta
from redteam_core.validator.miner_manager import MinerManager, ScoringLog, ChallengeRecord

@pytest.fixture
def miner_manager():
    return MinerManager(challenge_name="test_challenge", challenge_incentive_weight=1.0)

def test_initialization(miner_manager):
    assert miner_manager.challenge_name == "test_challenge"
    assert miner_manager.challenge_incentive_weight == 1.0
    assert miner_manager.uids_to_commits == {}
    assert miner_manager.challenge_records == {}

def test_update_scores(miner_manager):
    logs = [
        ScoringLog(uid=1, score=10.0, miner_input={}, miner_output=None, miner_docker_image="image1"),
        ScoringLog(uid=2, score=20.0, miner_input={}, miner_output=None, miner_docker_image="image2"),
    ]
    miner_manager.update_scores(logs)
    today = datetime.now().strftime("%Y-%m-%d")
    assert today in miner_manager.challenge_records
    assert miner_manager.challenge_records[today].score == 20.0
    assert miner_manager.challenge_records[today].uid == 2

def test_get_onchain_scores(miner_manager):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    miner_manager.challenge_records[today] = ChallengeRecord(point=100, score=100, date=today, uid=1)
    miner_manager.challenge_records[yesterday] = ChallengeRecord(point=50, score=50, date=yesterday, uid=2)

    n_uids = 3
    scores = miner_manager.get_onchain_scores(n_uids)
    assert scores[1] > scores[2], "Score of uid 1 should be greater than uid 2 because one of the records has been submited erlier"
    assert scores[0] == 0 , "Score of uid 0 should be 0 because it has no record"