import hashlib
import datetime

import base58
import requests
import numpy as np
import bittensor as bt

from redteam_core.constants import constants
from redteam_core.validator.challenge_manager import ChallengeManager


class MinerManager:
    def __init__(
        self,
        metagraph: bt.metagraph,
        challenge_managers: dict[str, ChallengeManager] = {},
    ):
        """
        Initializes the MinerManager to track scores and challenges.
        """
        self.metagraph = metagraph
        self.challenge_managers = challenge_managers

    def update_challenge_managers(
        self, challenge_managers: dict[str, ChallengeManager]
    ):
        self.challenge_managers = challenge_managers

    def _get_challenge_scores(self, n_uids: int) -> np.ndarray:
        """
        Aggregate challenge scores for all miners from all challenges using challenge managers.
        Combines scores from each challenge based on their incentive weights and applies
        time-based decay to historical scores.

        Args:
            n_uids (int): Number of UIDs in the network

        Returns:
            np.ndarray: Aggregated and normalized scores for all miners
        """
        aggregated_scores = np.zeros(n_uids)

        # Process each challenge
        for _, challenge_manager in self.challenge_managers.items():
            challenge_weight = challenge_manager.challenge_incentive_weight
            challenge_scores = challenge_manager.get_challenge_scores()

            bt.logging.debug(
                f"[MINER MANAGER] Challenge {challenge_manager.challenge_name} challenge_weight: {challenge_weight}\n "
                f"Challenge scores: {challenge_scores.tolist()}\n "
            )

            # Add weighted scores to aggregate
            aggregated_scores += challenge_scores * challenge_weight

        if np.sum(aggregated_scores) > 0:
            aggregated_scores /= np.sum(aggregated_scores)

        bt.logging.debug(
            f"[MINER MANAGER] Aggregated challenge scores: {aggregated_scores.tolist()}"
        )

        return aggregated_scores

    def _get_newly_registration_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on newly registration, high for more recent registrations.
        Only considers UIDs registered within the immunity period (defined in blocks).
        Scores range from 1.0 (just registered) to 0.0 (older than immunity period).
        """
        scores = np.zeros(n_uids)
        current_time = datetime.datetime.now(datetime.timezone.utc)
        endpoint = constants.STORAGE_API.URL + "/fetch-uids-registration-time"

        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            uids_registration_time = response.json()["data"]

            # Process uids_registration_time to get the scores
            for uid, registration_time in uids_registration_time.items():
                uid = int(uid)
                if uid >= n_uids:
                    continue

                # Parse the UTC datetime string
                reg_time = datetime.datetime.strptime(
                    registration_time, "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=datetime.timezone.utc)

                seconds_since_registration = (current_time - reg_time).total_seconds()
                blocks_since_registration = seconds_since_registration / 12

                # Only consider UIDs registered within immunity period
                if blocks_since_registration <= constants.SUBNET_IMMUNITY_PERIOD:
                    # Score decreases linearly from 1.0 (just registered) to 0.0 (immunity period ended)
                    scores[uid] = max(
                        0,
                        1.0
                        - (
                            blocks_since_registration / constants.SUBNET_IMMUNITY_PERIOD
                        ),
                    )

            # Normalize scores if any registrations exist
            if np.sum(scores) > 0:
                scores = scores / np.sum(scores)

        except Exception as e:
            bt.logging.error(f"Error fetching uids registration time: {e}")
            return np.zeros(n_uids)

        bt.logging.debug(
            f"[MINER MANAGER] Newly registration scores: {scores.tolist()}"
        )

        return scores

    def _get_alpha_stake_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on alpha stake, high for more stake.
        Uses square root transformation to reduce the impact of very high stakes, encourage small holders.
        """
        scores = np.zeros(n_uids)
        # Apply square root transformation to reduce the impact of high stakes
        sqrt_alpha_stakes = np.sqrt(self.metagraph.alpha_stake)
        total_sqrt_alpha_stakes = np.sum(sqrt_alpha_stakes)
        if total_sqrt_alpha_stakes > 0:
            # Normalize stakes to get scores between 0 and 1
            scores = sqrt_alpha_stakes / total_sqrt_alpha_stakes

        bt.logging.debug(f"[MINER MANAGER] Alpha stake scores: {scores.tolist()}")

        return scores

    def _get_alpha_burn_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on alpha burn, high for more burn.
        """
        # Find owner 's hotkey
        scores = np.zeros(n_uids)
        try:
            public_key_bytes = self.metagraph.owner_hotkey[0]
            # Convert to bytes
            public_key_bytes = bytes(public_key_bytes)
            # Prefix for Substrate address
            prefix = 42
            prefix_bytes = bytes([prefix])

            input_bytes = prefix_bytes + public_key_bytes

            # Calculate checksum (blake2b-512)
            blake2b = hashlib.blake2b(digest_size=64)
            blake2b.update(b"SS58PRE" + input_bytes)
            checksum = blake2b.digest()
            checksum_bytes = checksum[:2]  # Take first two bytes of checksum

            # Final bytes = prefix + public key + checksum
            final_bytes = input_bytes + checksum_bytes

            # Convert to base58
            owner_hotkey_base58 = base58.b58encode(final_bytes).decode()

            # Get the index of the owner hotkey
            owner_hotkey_index = self.metagraph.hotkeys.index(owner_hotkey_base58)

            # Set alpha burn score to 1.0
            scores[owner_hotkey_index] = 1.0
        except Exception as e:
            bt.logging.error(f"Error calculating alpha burn score: {e}")
            return np.zeros(n_uids)

        bt.logging.debug(f"[MINER MANAGER] Alpha burn scores: {scores.tolist()}")

        return scores

    def get_onchain_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of weighted scores combining:
        1. Challenge scores (based on performance improvements)
        2. Newly registration scores (favoring recently registered UIDs)
        3. Alpha stake scores (based on stake amount)

        Weights are defined in constants:
        - CHALLENGE_SCORES_WEIGHT (45%)
        - ALPHA_STAKE_WEIGHT (5%)
        - ALPHA_BURN_WEIGHT (50%)
        """
        # Get challenge performance scores
        challenge_scores = self._get_challenge_scores(n_uids)

        # Get newly registration scores (disabled)
        # registration_scores = self._get_newly_registration_scores(n_uids)

        # Get alpha stake scores
        alpha_stake_scores = self._get_alpha_stake_scores(n_uids)

        # Get alpha burn scores
        alpha_burn_scores = self._get_alpha_burn_scores(n_uids)

        # Combine scores using weights from constants
        final_scores = (
            challenge_scores * constants.CHALLENGE_SCORES_WEIGHT
            # + registration_scores * constants.NEWLY_REGISTRATION_WEIGHT
            + alpha_stake_scores * constants.ALPHA_STAKE_WEIGHT
            + alpha_burn_scores * constants.ALPHA_BURN_WEIGHT
        )

        bt.logging.debug(
            f"[MINER MANAGER] Onchain final scores: {final_scores.tolist()}\n "
        )

        return final_scores
