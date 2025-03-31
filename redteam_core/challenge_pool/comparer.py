import bittensor as bt
import requests
import time
from typing import Union
import traceback

import docker

from redteam_core.challenge_pool.base import BaseComparer
from redteam_core.validator.models import MinerChallengeCommit, ComparisonLog, ScoringLog
from redteam_core.challenge_pool import docker_utils
from redteam_core.constants import constants


class Comparer(BaseComparer):
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

        self.docker_client = docker_utils.create_docker_client()

        self.local_network = "redteam_local"

    def start_comparison(self):
        """
        Start the comparison process:
        1. Setup challenge container for comparison
        2. For each miner, process their comparison logs by sending to /compare endpoint
        3. Update comparison logs with results
        4. Optionally compare commits within the same batch
        """
        try:
            # Setup challenge container
            self._setup_challenge()

            # Process each miner's comparison logs
            for miner_commit in self.miner_commits:
                bt.logging.info(
                    f"[COMPARER] Processing comparison logs for miner {miner_commit.miner_hotkey}"
                )

                # Process existing comparison logs
                self._process_existing_comparison_logs(miner_commit)

                # Compare with other commits in the same batch if required
                if self.compare_with_each_other:
                    self._compare_within_batch(miner_commit)

            # Clean up challenge container
            docker_utils.remove_container(
                client=self.docker_client,
                container_name=self.challenge_name,
                stop_timeout=360,
                force=True,
                remove_volumes=True,
            )
            docker_utils.clean_docker_resources(
                client=self.docker_client,
                remove_containers=True,
                remove_images=True,
                remove_networks=True,
                prune_volumes=True,
                prune_builds=True
            )

        except Exception as e:
            bt.logging.error(
                f"[COMPARER] Error in comparison process: {traceback.format_exc()}"
            )
            raise

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
                    log.error
                    or log.miner_output is None
                    or log.reference_output is None
                ):
                    continue

                if log.similarity_score is not None:
                    # Skip if similarity score is already set
                    continue

                try:
                    # Send to /compare endpoint
                    similarity_score = self._compare_outputs(
                        miner_input=log.miner_input,
                        miner_output=log.miner_output,
                        reference_output=log.reference_output,
                    )
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
        Only compares with commits that have smaller UIDs.
        Prioritizes comparing outputs that were generated from the same inputs.
        """
        # Skip if no scoring logs
        if not miner_commit.scoring_logs:
            return

        # Group scoring logs by input hash for efficient matching
        miner_logs_by_hash: dict[str, ScoringLog] = {}
        for log in miner_commit.scoring_logs:
            if log.input_hash and log.miner_output:
                miner_logs_by_hash[log.input_hash] = log

        for other_commit in self.miner_commits:
            # Only compare with commits that have smaller UIDs
            if other_commit.miner_uid >= miner_commit.miner_uid:
                continue

            # Skip if we've already compared with this commit
            if other_commit.docker_hub_id in miner_commit.comparison_logs:
                continue

            # Skip if other commit has no scoring logs
            if not other_commit.scoring_logs:
                continue

            # Find matching inputs between the two commits
            comparison_logs = []

            # Check each scoring log in the other commit to find matching inputs
            for other_log in other_commit.scoring_logs:
                if not other_log.input_hash or not other_log.miner_output:
                    continue

                # If we have a matching input hash, we can compare outputs
                if other_log.input_hash in miner_logs_by_hash:
                    miner_log = miner_logs_by_hash[other_log.input_hash]

                    try:
                        # Use the comparison API to compare outputs
                        similarity_score = self._compare_outputs(
                            miner_input=miner_log.miner_input,  # Both used the same input
                            miner_output=miner_log.miner_output,
                            reference_output=other_log.miner_output
                        )

                        # Create a comparison log with the inputs and outputs
                        comparison_log = ComparisonLog(
                            similarity_score=similarity_score,
                            miner_input=miner_log.miner_input,
                            miner_output=miner_log.miner_output,
                            reference_output=other_log.miner_output,
                            reference_hotkey=other_commit.miner_hotkey,
                        )
                        comparison_logs.append(comparison_log)

                    except Exception as e:
                        bt.logging.error(
                            f"Error comparing outputs with matching inputs for miner {miner_commit.miner_hotkey}: {str(e)}"
                        )
                        comparison_log = ComparisonLog(
                            error=str(e),
                            similarity_score=0.0,
                            miner_input=miner_log.miner_input,
                            miner_output=miner_log.miner_output,
                            reference_output=other_log.miner_output,
                            reference_hotkey=other_commit.miner_hotkey,
                        )
                        comparison_logs.append(comparison_log)

            # If we found any matching inputs, add the comparison logs
            if comparison_logs:
                miner_commit.comparison_logs[other_commit.docker_hub_id] = comparison_logs
                bt.logging.info(
                    f"[COMPARER] Added {len(comparison_logs)} comparison logs for commit {miner_commit.encrypted_commit} against docker_hub_id {other_commit.docker_hub_id}"
                )
            else:
                bt.logging.warning(
                    f"[COMPARER] No matching inputs found for comparison between commit {miner_commit.encrypted_commit} and docker_hub_id {other_commit.docker_hub_id}"
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

            similarity_score = response.json()

            # Normalize score to float between 0 and 1
            if isinstance(similarity_score, int):
                similarity_score = float(similarity_score)
            elif not isinstance(similarity_score, float):
                similarity_score = 0.0

            return max(0.0, min(1.0, similarity_score))

        except Exception as e:
            bt.logging.error(f"Error in comparison request: {str(e)}")
            return 0.0

    def _setup_challenge(self):
        """
        Sets up the challenge environment by building and running the challenge container
        in an isolated Docker network. Includes building the image, creating the network,
        and verifying the container's health status.
        """
        # Build challenge image
        docker_utils.build_challenge_image(
            client=self.docker_client,
            challenge_name=self.challenge_name,
            build_path=f"redteam_core/challenge_pool/{self.challenge_name}",
        )

        # Remove existing challenge container
        docker_utils.remove_container(
            client=self.docker_client,
            container_name=self.challenge_name,
            stop_timeout=360,
            force=True,
            remove_volumes=True,
        )

        # Create network
        docker_utils.create_network(
            client=self.docker_client,
            network_name=self.local_network,
            allow_internet=False,
        )

        # Run challenge container
        self.challenge_container = docker_utils.run_container(
            client=self.docker_client,
            image=self.challenge_name,
            detach=True,
            ports={
                f"{constants.CHALLENGE_DOCKER_PORT}/tcp": constants.CHALLENGE_DOCKER_PORT
            },
            **self.challenge_info.get("challenge_container_run_kwargs", {}),
        )
        bt.logging.info(
            f"[COMPARER] Challenge container started: {self.challenge_container.status}"
        )

        # Check challenge container health
        self._check_container_alive(
            self.challenge_container,
            health_port=constants.CHALLENGE_DOCKER_PORT,
            is_challenger=True,
        )

    def _check_alive(self, port=10001, is_challenger=True) -> bool:
        """
        Checks if the challenge container is still running.
        """

        _protocol, _ssl_verify = self._check_protocol(is_challenger=is_challenger)

        try:
            response = requests.get(
                f"{_protocol}://localhost:{port}/health",
                verify=_ssl_verify,
            )
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            return False
        return False

    def _check_protocol(
        self, is_challenger: bool = True
    ) -> tuple[str, Union[bool, None]]:
        """Check the protocol scheme and SSL/TLS verification for the challenger or miner.

        Args:
            is_challenger (bool, optional): Flag to check the protocol for the challenger or miner. Defaults to True.

        Returns:
            Tuple[str, Union[bool, None]]: A tuple containing the protocol scheme and SSL/TLS verification.
        """

        _protocol = "http"
        _ssl_verify: Union[bool, None] = None

        if "protocols" in self.challenge_info:
            _protocols = self.challenge_info["protocols"]

            if is_challenger:
                if "challenger" in _protocols:
                    _protocol = _protocols["challenger"]

                if "challenger_ssl_verify" in _protocols:
                    _ssl_verify = _protocols["challenger_ssl_verify"]

            if not is_challenger:
                if "miner" in _protocols:
                    _protocol = _protocols["miner"]

                if "miner_ssl_verify" in _protocols:
                    _ssl_verify = _protocols["miner_ssl_verify"]

        return _protocol, _ssl_verify

    def _check_container_alive(
        self,
        container: docker.models.containers.Container,
        health_port,
        is_challenger=True,
        timeout=None,
        start_time=None,
    ):
        """Check when the container is running successfully"""
        if not start_time:
            start_time = time.time()
        while not self._check_alive(port=health_port, is_challenger=is_challenger) and (
            not timeout or time.time() - start_time < timeout
        ):
            container.reload()
            if container.status in ["exited", "dead"]:
                container_logs = container.logs().decode("utf-8", errors="ignore")
                bt.logging.error(
                    f"[COMPARER] Container {container} failed with status: {container.status}"
                )
                bt.logging.error(f"[COMPARER] Container logs:\n{container_logs}")
                raise RuntimeError(
                    f"[COMPARER] Container failed to start. Status: {container.status}. Container logs: {container_logs}"
                )
            else:
                bt.logging.info(
                    f"[COMPARER] Waiting for container to start. {container.status}"
                )
                time.sleep(5)
