import os
import datetime
from typing import Callable

TESTNET = os.getenv("TESTNET", False) == "1"

__version__ = "0.0.1"
version_split = __version__.split(".")
__spec_version__ = (
    (1000 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
)

N_CHALLENGES_PER_EPOCH = 10
SCORING_HOUR = 14
DATETIME_TO_SCORING: Callable[[datetime.datetime], bool] = (
    lambda x: x.hour == SCORING_HOUR
)
CHALLENGE_DOCKER_PORT = 10001
MINER_DOCKER_PORT = 10002

REVEAL_INTERVAL = 60 * 60 * 24 if not TESTNET else 30
EPOCH_LENGTH = 60 * 60 if not TESTNET else 30
MIN_VALIDATOR_STAKE = 1000000 if not TESTNET else -1

N_LAST_SCORES = 10

QUERY_TIMEOUT = 4
