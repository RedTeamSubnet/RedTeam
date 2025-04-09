import asyncio
import copy

import aiohttp
import bittensor as bt

from redteam_core.challenge_pool.controller import Controller
from redteam_core.validator.models import MinerChallengeCommit, ScoringLog, ComparisonLog
from redteam_core.constants import constants

class ResponseQualityAdversarialController(Controller):

    # Override the _score_miner_with_new_inputs method
    def _score_miner_with_new_inputs(self, miner_commit: MinerChallengeCommit, challenge_inputs):
        """
        Run and score miner with new challenge inputs.
        This method try to make async calls to miner to get the responses
        and async calls to challenge container to get the scores
        """
        # Get async loop
        loop = asyncio.get_event_loop()

        # Get miner responses and scores asynchronously
        results = loop.run_until_complete(
            self._gather_async_responses_and_scores(challenge_inputs)
        )

        # Process the results
        for i, (miner_input, miner_output, score, error_message) in enumerate(results):
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

    async def _gather_async_responses_and_scores(self, challenge_inputs):
        """
        Gather all miner responses and scores asynchronously.
        """
        async with aiohttp.ClientSession() as session:
            # First get all responses
            response_tasks = [self._async_submit_challenge_to_miner(session, challenge) for challenge in challenge_inputs]
            responses = await asyncio.gather(*response_tasks)

            # Then get all scores for valid responses
            score_tasks = []
            for i, (miner_input, miner_output, error_message) in enumerate(responses):
                if miner_output is not None:
                    score_task = self._async_score_challenge(session, miner_input, miner_output)
                    score_tasks.append(score_task)
                else:
                    score_tasks.append(asyncio.create_task(asyncio.sleep(0, result=0.0)))  # No score for failed response

            scores = await asyncio.gather(*score_tasks)

            # Combine responses with scores
            results = []
            for i, (miner_input, miner_output, error_message) in enumerate(responses):
                score = scores[i] if miner_output is not None else 0.0
                results.append((miner_input, miner_output, score, error_message))

            return results

    async def _gather_async_miner_responses(self, challenge_inputs):
        """
        Gather all miner responses asynchronously.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._async_submit_challenge_to_miner(session, challenge) for challenge in challenge_inputs]
            return await asyncio.gather(*tasks)

    async def _async_submit_challenge_to_miner(self, session: aiohttp.ClientSession, challenge):
        """
        Async version of _submit_challenge_to_miner
        """
        error_message = ""
        miner_input = copy.deepcopy(challenge)
        exclude_miner_input_key = self.challenge_info.get("exclude_miner_input_key", [])
        for key in exclude_miner_input_key:
            miner_input[key] = None
        try:
            _protocol, _ssl_verify = self._check_protocol(is_challenger=False)
            url = f"{_protocol}://localhost:{constants.MINER_DOCKER_PORT}/solve"

            timeout = aiohttp.ClientTimeout(total=self.challenge_info.get("challenge_solve_timeout", 60))
            async with session.post(url, json=miner_input, timeout=timeout, ssl=_ssl_verify) as response:
                miner_output = await response.json()
                return miner_input, miner_output, error_message

        except asyncio.TimeoutError:
            error_message = "Timeout occurred while trying to solve challenge."
            bt.logging.error(error_message)
            return miner_input, None, error_message
        except Exception as ex:
            error_message = f"Submit challenge to miner failed: {str(ex)}"
            bt.logging.error(error_message)
            return miner_input, None, error_message

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

    # Override the _run_reference_comparison_inputs method
    def _run_reference_comparison_inputs(self, miner_commit: MinerChallengeCommit):
        """
        Run miner with reference comparison commits inputs to compare performance.
        For each reference commit, we run the current miner against the inputs that were
        previously used to test that reference commit.
        """
        # Skip for baseline commit since it's used as reference
        if miner_commit.miner_uid == self.baseline_commit.miner_uid:
            return

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self._async_run_reference_comparisons(miner_commit)
        )

    async def _async_run_reference_comparisons(self, miner_commit: MinerChallengeCommit):
        """
        Async version of running reference comparisons.
        """
        async with aiohttp.ClientSession() as session:
            # Process each reference commit
            for reference_commit in self.reference_comparison_commits:
                bt.logging.info(
                    f"[CONTROLLER] Running comparison with reference commit {reference_commit.docker_hub_id}"
                )

                if reference_commit.docker_hub_id in miner_commit.comparison_logs:
                    # Already run this reference commit, skip
                    continue
                else:
                    miner_commit.comparison_logs[reference_commit.docker_hub_id] = []

                # Create tasks for each input from reference commit
                tasks = []
                for i, reference_log in enumerate(reference_commit.scoring_logs):
                    if reference_log.miner_input is None:
                        continue

                    task = self._async_process_reference_comparison(
                        session,
                        reference_log,
                        reference_commit.miner_hotkey
                    )
                    tasks.append(task)

                # Process all tasks concurrently
                comparison_results = await asyncio.gather(*tasks)

                # Add results to comparison logs
                for comparison_log in comparison_results:
                    if comparison_log:  # Skip None results
                        miner_commit.comparison_logs[reference_commit.docker_hub_id].append(comparison_log)

    async def _async_process_reference_comparison(self, session: aiohttp.ClientSession, reference_log, reference_hotkey):
        """
        Process a single reference comparison asynchronously.
        """
        # Submit the same input to current miner
        miner_input, miner_output, error_message = await self._async_submit_challenge_to_miner(
            session, reference_log.miner_input
        )

        if miner_input is None:
            return None

        # Create comparison log
        return ComparisonLog(
            miner_input=reference_log.miner_input,
            miner_output=miner_output,
            reference_output=reference_log.miner_output,
            error=error_message,
            reference_hotkey=reference_hotkey,
        )

