__version__ = "0.0.1"
version_split = __version__.split(".")
__spec_version__ = (
    (1000 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
)

N_CHALLENGES_PER_EPOCH = 10
CHALLENGE_DOCKER_PORT = 10001
MINER_DOCKER_PORT = 10002

REVEAL_INTERVAL = 60 * 60 * 24
EPOCH_LENGTH = 60 * 60
MIN_VALIDATOR_STAKE = 10000

N_LAST_SCORES = 10

QUERY_TIMEOUT = 10
