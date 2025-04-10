import asyncio
import traceback
import aiohttp
import bittensor as bt

from redteam_core.challenge_pool.controller import Controller
from redteam_core.validator.models import MinerChallengeCommit, ScoringLog
from redteam_core.constants import constants
from redteam_core.challenge_pool import docker_utils

class ResponseQualityAdversarialController(Controller):

    # Override the start_challenge to do async calls
    def start_challenge(self):
        """
        Initiates the challenge lifecycle by setting up and executing the challenge Docker container.

        This process involves:
        1. Building and running the challenge container within an isolated Docker network.
        2. Generating or retrieving challenge inputs to evaluate miners.
        3. Scoring a baseline Docker image, if specified, to establish a reference point.
        4. Iteratively running each miner's Docker container to submit and score their solutions.
        5. Collecting and logging the results, including any errors encountered during execution.
        6. Cleaning up Docker resources to ensure no residual containers or images remain.

        The method ensures that each miner's submission is evaluated against the challenge inputs,
        and comparison logs are generated to assess performance relative to reference commits.
        """
        # Setup challenge, get challenge container and network ready
        self._setup_challenge()

        # Generate new input to score miners
        num_task = self.challenge_info.get(
            "num_tasks", constants.N_CHALLENGES_PER_EPOCH
        )
        # Start with seed inputs and generate more if needed to reach num_task
        challenge_inputs = self.seed_inputs.copy()
        remaining_tasks = max(0, num_task - len(challenge_inputs))
        if remaining_tasks > 0:
            # Asynchronously generate more inputs
            loop = asyncio.get_event_loop()
            new_inputs = loop.run_until_complete(
                self._generate_new_inputs(remaining_tasks)
            )
            challenge_inputs.extend(new_inputs)

        # Score baseline first if it exists
        if self.baseline_commit.docker_hub_id:
            try:
                self._setup_miner_container(self.baseline_commit)
                self._score_miner_with_new_inputs(
                    self.baseline_commit, challenge_inputs
                )
                docker_utils.remove_container_by_port(
                    client=self.docker_client,
                    port=constants.MINER_DOCKER_PORT,
                )
                docker_utils.clean_docker_resources(
                    client=self.docker_client,
                    remove_containers=True,
                    remove_images=True,
                )
            except Exception as e:
                bt.logging.error(f"Error scoring baseline: {e}")
                bt.logging.error(traceback.format_exc())

        # Score commits with new input and collect comparison logs
        for miner_commit in self.miner_commits:
            uid, hotkey = miner_commit.miner_uid, miner_commit.miner_hotkey

            try:
                bt.logging.info(f"[CONTROLLER] Scoring miner {uid} - {hotkey} with commit {miner_commit.encrypted_commit}")
                # 1. Validate and setup miner container
                self._setup_miner_container(miner_commit)

                # 2. Score with new inputs
                self._score_miner_with_new_inputs(miner_commit, challenge_inputs)

                # 3. Run reference comparisons
                self._run_reference_comparison_inputs(miner_commit)

            except Exception as e:
                bt.logging.error(f"Error while processing miner {uid} - {hotkey}: {e}")
                bt.logging.error(traceback.format_exc())
                if uid != self.baseline_commit.miner_uid:
                    miner_commit.scoring_logs.append(
                        ScoringLog(
                            miner_input=None,
                            miner_output=None,
                            score=0,
                            error=str(e),
                        )
                    )

            # Clean up miner container
            docker_utils.remove_container_by_port(
                client=self.docker_client,
                port=constants.MINER_DOCKER_PORT,
            )
            docker_utils.clean_docker_resources(
                client=self.docker_client,
                remove_containers=True,
                remove_images=True,
            )

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
        )

    async def _generate_new_inputs(self, num_tasks: int) -> list[dict]:
        """
        Asynchronously generates new challenge inputs.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._async_get_challenge(session) for _ in range(num_tasks)]
            return await asyncio.gather(*tasks)

    async def _async_get_challenge(self, session: aiohttp.ClientSession) -> dict:
        """
        Async version to get a challenge from the container with retry logic.
        """
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)
        url = f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/task"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.get(url, ssl=_ssl_verify) as response:
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(
                        f"Failed to get challenge after {max_retries} attempts: {str(e)}"
                    )
                # Wait briefly before retrying
                await asyncio.sleep(1)

    # Override the _score_miner_with_new_inputs method
    def _score_miner_with_new_inputs(self, miner_commit: MinerChallengeCommit, challenge_inputs):
        """
        Run and score miner with new challenge inputs.
        This method:
        1. Makes synchronous calls to miner to get the responses (one by one)
        2. Collects all responses
        3. Then makes async calls to challenge container to get scores (in parallel)
        """
        # Step 1: Get all miner responses synchronously (one by one)
        responses = []
        for miner_input in challenge_inputs:
            # Get miner output using the synchronous method
            miner_output, error_message = self._submit_challenge_to_miner(miner_input)
            responses.append((miner_input, miner_output, error_message))

        # Step 2: Score all valid responses asynchronously (in parallel)
        loop = asyncio.get_event_loop()
        score_tasks = []
        for miner_input, miner_output, _ in responses:
            if miner_output is not None:
                score_tasks.append((miner_input, miner_output))

        # If we have tasks to score, run them in parallel
        if score_tasks:
            scores = loop.run_until_complete(
                self._score_challenges_async(score_tasks)
            )
        else:
            scores = []

        # Step 3: Create the scoring logs
        score_index = 0
        for i, (miner_input, miner_output, error_message) in enumerate(responses):
            # Get the score if available, otherwise use 0.0
            score = scores[score_index] if miner_output is not None and score_index < len(scores) else 0.0
            if miner_output is not None:
                score_index += 1

            log = ScoringLog(
                miner_input=miner_input,
                miner_output=miner_output,
                score=score,
                error=error_message,
            )

            # Handle baseline scoring separately
            if miner_commit.miner_hotkey == "baseline":
                self.baseline_commit.scoring_logs.append(log)
            else:
                # Adjust score relative to baseline if baseline exists and has been scored
                if (
                    self.baseline_commit.docker_hub_id
                    and len(self.baseline_commit.scoring_logs) > i
                ):
                    log.score -= self.baseline_commit.scoring_logs[i].score
                    log.baseline_score = self.baseline_commit.scoring_logs[i].score
                miner_commit.scoring_logs.append(log)

    async def _score_challenges_async(self, score_tasks):
        """
        Score multiple challenges asynchronously.

        Args:
            score_tasks: List of (miner_input, miner_output) tuples to score

        Returns:
            List of scores in the same order as the inputs
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._async_score_challenge(session, miner_input, miner_output)
                for miner_input, miner_output in score_tasks
            ]
            return await asyncio.gather(*tasks)

    async def _async_score_challenge(self, session: aiohttp.ClientSession, miner_input, miner_output):
        """
        Async version of _score_challenge
        """
        _protocol, _ssl_verify = self._check_protocol(is_challenger=True)
        try:
            payload = {
                "miner_input": miner_input,
                "miner_output": miner_output,
            }
            url = f"{_protocol}://localhost:{constants.CHALLENGE_DOCKER_PORT}/score"
            async with session.post(url, json=payload, ssl=_ssl_verify) as response:
                score = await response.json()
        except Exception as ex:
            bt.logging.error(f"Score challenge failed: {str(ex)}")
            score = 0.0

        if isinstance(score, int):
            score = float(score)
        elif not isinstance(score, float):
            score = 0.0
        return score
