import abc

from redteam_core.validator.models import MinerChallengeCommit


class BaseController(abc.ABC):
    """
    Template for a challenge controller. Each challenge should have its own controller that is implemented by this class, following the abstract method `start_challenge` and parameters in the constructor.
    """

    def __init__(
        self,
        challenge_name: str,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
        reference_comparison_commits: list[MinerChallengeCommit],
        seed_inputs: list[dict] = [],
    ):
        self.challenge_name = challenge_name
        self.challenge_info = challenge_info
        self.miner_commits = miner_commits
        self.reference_comparison_commits = reference_comparison_commits
        self.seed_inputs = seed_inputs

    @abc.abstractmethod
    def start_challenge(self):
        """
        Start the challenge, update the miner's score and reference comparison logs directly. Does not return anything.
        """
        pass
