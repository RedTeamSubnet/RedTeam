import abc

from redteam_core.validator.models import MinerChallengeCommit, ScoringLog

class BaseController(abc.ABC):
    """
    Template for a challenge controller. Each challenge should have its own controller that is implemented by this class, following the abstract method `start_challenge` and parameters in the constructor.
    """
    def __init__(
            self,
            challenge_info: dict,
            miner_commits: list[MinerChallengeCommit],
            reference_comparison_commits: list[MinerChallengeCommit],
        ):
        self.challenge_info = challenge_info
        self.miner_commits = miner_commits
        self.reference_comparison_commits = reference_comparison_commits

        self.challenge_name = challenge_info["name"]

    @abc.abstractmethod
    def start_challenge(self):
        """
        Start the challenge, update the miner's score and reference comparison logs directly. Does not return anything.
        """
        pass


class BaseComparer:
    """
    Template for a challenge comparer. Each challenge should have its own comparer that is implemented by this class, following the abstract method `compare` and parameters in the constructor.
    """
    def __init__(
        self,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
    ):
        self.challenge_info = challenge_info
        self.miner_commits = miner_commits

        self.challenge_name = challenge_info["name"]

    @abc.abstractmethod
    def start_comparision(self):
        """
        Start the comparision, update the miner's comparison logs directly. Does not return anything.
        """
        pass