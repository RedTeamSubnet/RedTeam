import bittensor as bt
import requests

from redteam_core.constants import constants
from redteam_core.challenge_pool.comparer import Comparer
from redteam_core.validator.models import (
    MinerChallengeCommit,
    ComparisonLog,
    ScoringLog,
)

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

    def _process_existing_comparison_logs(self, miner_commit: MinerChallengeCommit):
        """
        Process existing comparison logs to fill in missing similarity scores.
        """
        for (
            reference_docker_hub_id,
            comparison_logs,
        ) in miner_commit.comparison_logs.items():
            for log in comparison_logs:
                if (
                    not log
                    or log.reference_output is None  # skip if no reference output
                    or log.similarity_score is not None  # skip if already compared
                ):
                    bt.logging.warning(
                        f"[COMPARER] Skipping comparison log for miner {miner_commit.miner_hotkey} against {reference_docker_hub_id}"
                    )
                    continue

                try:
                    # Send to /compare endpoint
                    _sorted_miner_commits = sorted(
                        [
                            commit
                            for commit in miner_commit.scoring_logs
                            if commit.miner_output["log_time"] is not None
                        ],
                        key=lambda x: x.miner_output["log_time"],
                    )

                    _latest_commit = (
                        _sorted_miner_commits[-1]
                        if _sorted_miner_commits
                        else miner_commit.scoring_logs[-1]
                    )

                    similarity_score = self._compare_outputs(
                        miner_input=log.miner_input,
                        miner_output=_latest_commit.miner_output,
                        reference_output=log.reference_output,
                    )

                    ###  Assign previous similarity score if the reference hotkey is the same as the miner hotkey
                    if miner_commit.miner_hotkey == log.reference_hotkey:
                        if similarity_score > 0.87:
                            if len(miner_commit.scoring_logs) > 1:
                                # get index of latest commit score and get previous commit score then subtract to find a difference
                                _scoring_log_index = miner_commit.scoring_logs.index(
                                    _latest_commit
                                )
                                if _scoring_log_index > 0:
                                    _previous_commit = miner_commit.scoring_logs[
                                        _scoring_log_index - 1
                                    ]
                                    _previous_commit_score = _previous_commit.get(
                                        "score", 0
                                    )
                                    _latest_commit_score = _latest_commit.get(
                                        "score", 0
                                    )
                                    _score_difference = abs(
                                        _previous_commit_score - _latest_commit_score
                                    )
                                    if not _score_difference > 0.05:
                                        bt.logging.info(
                                            f"[COMPARER] Comparing with own scripts. Score is same so assigneing 1 to similarity score for miner {miner_commit.miner_hotkey}"
                                        )
                                        similarity_score = 1
                                    else:
                                        bt.logging.info(
                                            f"[COMPARER] Comparing with own scripts. Score is different so assigneing 0.1 to similarity score for miner {miner_commit.miner_hotkey}"
                                        )
                                        similarity_score = 0.1
                    log.similarity_score = similarity_score

                except Exception as e:
                    bt.logging.error(
                        f"[COMPARER] Error comparing outputs for miner {miner_commit.miner_hotkey}: {str(e)}"
                    )
                    log.error = str(e)
                    log.similarity_score = 0.0

    def _compare_within_batch(self, miner_commit: MinerChallengeCommit):
        """
        Compare commits within the same batch if compare_with_each_other is True.
        Prioritizes comparing outputs that were generated from the same inputs.
        """

        if not miner_commit.scoring_logs:
            return

        # Group scoring logs by input hash for efficient matching
        _current_miner_logs_by_hash: dict[str, ScoringLog] = {}
        for log in miner_commit.scoring_logs:
            if log.input_hash and log.miner_output:
                _current_miner_logs_by_hash[log.input_hash] = log

        for _other_miner_commit in self.miner_commits:
            ### Check if we should compare with this commit
            if (
                _other_miner_commit.commit_timestamp
                > miner_commit.commit_timestamp  # Newer commit
                or _other_miner_commit.docker_hub_id
                in miner_commit.comparison_logs  # Already compared
                or not _other_miner_commit.scoring_logs  # No scoring logs
                or miner_commit.miner_hotkey == _other_miner_commit.miner_hotkey
            ):  # Same miner
                bt.logging.debug(
                    f"[COMPARER - HBComparer]Skipping comparing with batch {_other_miner_commit.miner_uid} for miner {miner_commit.miner_hotkey}"
                )
                continue

            # Find matching inputs between the two commits
            comparison_logs = []

            # Check each scoring log in the other commit to find matching inputs
            for _other_log in _other_miner_commit.scoring_logs:

                # skip if no input hash or miner output
                if not _other_log.input_hash or not _other_log.miner_output:
                    continue

                # If we have a matching input hash, we can compare outputs
                if _other_log.input_hash in _current_miner_logs_by_hash:
                    miner_log = _current_miner_logs_by_hash[_other_log.input_hash]
                    try:
                        _miner_output = miner_log.miner_output

                        if not _miner_output:
                            bt.logging.warning(
                                f"[COMPARER - HBComparer] miner_output is None for miner {miner_commit.miner_uid}"
                            )
                            log.error = "miner_output is None"
                            log.similarity_score = 0.0

                        # Use the comparison API to compare outputs
                        similarity_score = self._compare_outputs(
                            miner_input=miner_log.miner_input,  # Both used the same input
                            miner_output=_miner_output,
                            reference_output=_other_log.miner_output,
                        )
                        # Remove huge bot.py from `outputs` to save size
                        if "bot_py" in _miner_output:
                            _miner_output["bot_py"] = None
                        if "bot_py" in _other_log.miner_output:
                            _other_log.miner_output["bot_py"] = None

                        # Create a comparison log with the inputs and outputs
                        comparison_log = ComparisonLog(
                            similarity_score=similarity_score,
                            miner_input=miner_log.miner_input,
                            miner_output=None,
                            reference_output=_other_log.miner_output,
                            reference_hotkey=_other_miner_commit.miner_hotkey,
                        )
                        comparison_logs.append(comparison_log)

                    except Exception as e:
                        bt.logging.error(
                            f"[COMPARER - HBComparer] Error comparing outputs with matching inputs for miner {miner_commit.miner_hotkey}: {str(e)}"
                        )
                        if miner_log and _other_log:
                            miner_log.miner_output["bot_py"] = None
                            _other_log.miner_output["bot_py"] = None
                            comparison_log = ComparisonLog(
                                error=str(e),
                                similarity_score=0.0,
                                miner_input=miner_log.miner_input,
                                miner_output=miner_log.miner_output,
                                reference_output=_other_log.miner_output,
                                reference_hotkey=_other_miner_commit.miner_hotkey,
                            )
                            comparison_logs.append(comparison_log)

            # If we found any matching inputs, add the comparison logs
            if comparison_logs:
                miner_commit.comparison_logs[_other_miner_commit.docker_hub_id] = (
                    comparison_logs
                )
                bt.logging.info(
                    f"[COMPARER] Added {len(comparison_logs)} comparison logs for commit {miner_commit.encrypted_commit} against docker_hub_id {_other_miner_commit.docker_hub_id}"
                )
            else:
                bt.logging.warning(
                    f"[COMPARER] No matching inputs found for comparison between commit {miner_commit.encrypted_commit} and docker_hub_id {_other_miner_commit.docker_hub_id}"
                )

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
            similarity_score = data.get("similarity_score", 1.0)

            # Normalize score to float between 0 and 1
            if isinstance(similarity_score, int):
                similarity_score = float(similarity_score)
            elif not isinstance(similarity_score, float):
                similarity_score = 1.0

            return max(0.0, min(1.0, similarity_score))

        except Exception as e:
            bt.logging.error(f"Error in comparison request: {str(e)}")
            return 0.0
