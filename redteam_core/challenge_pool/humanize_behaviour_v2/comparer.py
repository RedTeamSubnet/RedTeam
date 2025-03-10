import bittensor as bt
import requests

from redteam_core.challenge_pool.comparer import Comparer
from redteam_core.validator.models import MinerChallengeCommit
from redteam_core.constants import constants

COMPARE_SCORE_THRESHOLD = 0.0


class HBComparer(Comparer):
    def __init__(
        self,
        challenge_name: str,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
        compare_with_each_other: bool,
    ):
        super().__init__(
            challenge_name=challenge_name,
            challenge_info=challenge_info,
            miner_commits=miner_commits,
            compare_with_each_other=compare_with_each_other,
        )

    def start_comparison(self):
        """
        Start the comparison process:
        1. Setup challenge container for comparison
        2. For each miner, process their comparison logs by sending to /compare endpoint
        3. Update comparison logs with results
        """
        try:
            bt.logging.info("[START COMPARISON - HBComparer] Starting comparison process")
            # Setup challenge container
            self._setup_challenge()

            # Process each miner's comparison logs
            for miner_commit in self.miner_commits:

                bt.logging.info(
                    f"[START COMPARISON] Processing miner {miner_commit.miner_hotkey}"
                )

                bt.logging.info(f"Miner data: {miner_commit}")

                bt.logging.info(
                    f"Processing comparison logs for miner {miner_commit.miner_hotkey}"
                )

                # Process each reference commit's comparison logs
                for (
                    reference_docker_hub_id,
                    comparison_logs,
                ) in miner_commit.comparison_logs.items():
                    for log in comparison_logs:
                        # TODO: Think how to handle errors
                        if (
                            log.error
                            or log.miner_output is None
                            or log.reference_output is None
                        ):
                            continue

                        if log.similarity_score is not None:
                            # Skip if similarity score is already set, already compared
                            continue

                        try:
                            # Send to /compare endpoint
                            similarity_score = self._compare_outputs(
                                miner_input=log.miner_input,
                                miner_output=log.miner_output,
                                reference_output=log.reference_output,
                            )

                            print(
                                "[START COMPARISON] Similarity score: ",
                                similarity_score,
                            )

                            log.similarity_score = similarity_score

                        except Exception as e:
                            bt.logging.error(
                                f"Error comparing outputs for miner {miner_commit.miner_hotkey}: {str(e)}"
                            )
                            log.error = str(e)
                            log.similarity_score = 0.0

        except Exception as e:
            bt.logging.error(f"Error in comparison process: {str(e)}")
            raise
        # finally:
        #     self._cleanup_challenge()

    def _compare_outputs(
        self, miner_input: dict, miner_output: dict, reference_output: dict
    ) -> float:
        """
        Send comparison request to challenge container's /compare endpoint.

        Args:
            miner_input: The input used for both outputs
            miner_output: The output from the current miner
            reference_output: The output from the reference miner

        Returns:
            float: Comparison score between 0 and 1
        """
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)

        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
                "reference_output": reference_output,
            }

            response = requests.post(
                f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/compare",
                timeout=self.challenge_info.get("challenge_compare_timeout", 60),
                verify=_ssl_verify,
                json=payload,
            )

            response_data = response.json()
            data = response_data.get("data", {})
            similarity_score = data.get("similarity_score", 0.0)

            # Normalize score to float between 0 and 1
            if isinstance(similarity_score, int):
                similarity_score = float(similarity_score)
            elif not isinstance(similarity_score, float):
                similarity_score = 0.0

            return max(0.0, min(1.0, similarity_score))

        except Exception as e:
            bt.logging.error(f"Error in comparison request: {str(e)}")
            return 0.0