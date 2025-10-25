from collections import defaultdict
import datetime
from typing import Any

from git import List
import requests
import numpy as np
import bittensor as bt
from typing import Dict

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
        valid_weights_sum = 0.0
        weights_to_redistribute = 0.0
        valid_challenges = []

        # First pass to identify valid challenges and collect unused weights
        for manager in self.challenge_managers.values():
            challenge_scores = manager.get_challenge_scores()
            score_sum = np.sum(challenge_scores)

            if score_sum == 0:
                weights_to_redistribute += manager.challenge_incentive_weight
            else:
                valid_weights_sum += manager.challenge_incentive_weight
                valid_challenges.append(manager)

        # Distribute leftover weights proportionally among valid challenges
        for manager in valid_challenges:
            adjusted_weight = manager.challenge_incentive_weight
            if valid_weights_sum > 0:
                adjusted_weight += (
                    weights_to_redistribute
                    * manager.challenge_incentive_weight
                    / valid_weights_sum
                )

            challenge_scores = manager.get_challenge_scores()
            normalized_challenge_scores = self.exclude_same_miner(challenge_scores)
            bt.logging.info(
                f"Challenge {manager.challenge_name} challenge_scores: {normalized_challenge_scores.tolist()}, adjusted_weight: {adjusted_weight}"
            )
            aggregated_scores += normalized_challenge_scores * adjusted_weight
        bt.logging.debug(
            f"Aggregated challenge scores: {aggregated_scores.tolist()}, valid_weights_sum: {valid_weights_sum}, weights_to_redistribute: {weights_to_redistribute}"
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

        bt.logging.debug(f"Newly registration scores: {scores.tolist()}")

        return scores

    def _get_alpha_stake_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on alpha stake, high for more stake.
        Uses square root transformation to reduce the impact of very high stakes, encourage small holders.
        """
        scores = np.zeros(n_uids)
        sqrt_alpha_stakes = np.sqrt(self.metagraph.alpha_stake)

        # Segment scores by coldkey
        coldkey_to_uids = {}
        for uid, coldkey in enumerate(self.metagraph.coldkeys):
            if coldkey not in coldkey_to_uids:
                coldkey_to_uids[coldkey] = []
            coldkey_to_uids[coldkey].append(uid)

        # Sum up sqrt stakes for each coldkey and assign to first UID
        for coldkey, uids in coldkey_to_uids.items():
            total_sqrt_stake = sum(sqrt_alpha_stakes[uid] for uid in uids)
            scores[uids[0]] = total_sqrt_stake

            # Zero out other UIDs for this coldkey
            for uid in uids[1:]:
                scores[uid] = 0

        # Normalize scores
        total_scores = np.sum(scores)
        if total_scores > 0:
            scores = scores / total_scores

        bt.logging.debug(f"Alpha stake scores: {scores.tolist()}")

        return scores

    def exclude_same_miner(
        self,
        scores,
        ignore_ip: str = "0.0.0.0",
    ) -> np.ndarray:
        """
        Keep only the best-scoring submission among miners that are considered the same entity.
        'Same entity' is defined as any submissions that share an IP or have overlapping coldkeys
        (across one or more IPs). Among each connected group, only the max score is kept.

        Returns:
            normalized_scores: np.ndarray of length num_uids (sum to 1, or all zeros if no scores)
            final_scores:      np.ndarray of length num_uids (only best submissions retained)
        """
        if sum(scores) == 0:
            return scores

        ips = [axon.ip for axon in self.metagraph.axons]
        coldkeys = [axon.coldkey for axon in self.metagraph.axons]
        _final_scores = np.zeros(self.metagraph.n, dtype=float)
        num_uids = int(self.metagraph.n)

        if num_uids is None:
            num_uids = max(len(ips), len(coldkeys), len(scores))

        # 1) Group submissions by IP (skip zeros up front)
        #    ip_groups[ip] -> list of dicts with index, coldkey, score
        ip_groups: Dict[str, Dict[str, List[Any]]] = defaultdict(
            lambda: {"index": [], "coldkey": [], "score": []}
        )
        for idx, (ip, ck, sc) in enumerate(zip(ips, coldkeys, scores)):
            if sc == 0:
                continue
            ip_groups[ip]["index"].append(idx)
            ip_groups[ip]["coldkey"].append(ck)
            ip_groups[ip]["score"].append(sc)

        # Optionally drop a placeholder IP
        if ignore_ip in ip_groups:
            del ip_groups[ignore_ip]

        if not ip_groups:
            # No positive scores left
            return np.zeros(num_uids)

        _miner_info = {}
        _count = 0
        for index, (ip, info) in enumerate(ip_groups.items()):
            if index == 0:
                _miner_info[f"miner_{_count}"] = {**info, "ip": [ip]}
                continue
            _is_new_miner = True
            for miner_info in _miner_info.values():
                if not set(info["coldkey"]).isdisjoint(set(miner_info["coldkey"])):
                    miner_info["index"].extend(info["index"])
                    miner_info["coldkey"].extend(info["coldkey"])
                    miner_info["score"].extend(info["score"])
                    miner_info.setdefault("ip", []).append(ip)
                    _is_new_miner = False

            if _is_new_miner:
                _miner_info[f"miner_{_count}"] = {**info, "ip": [ip]}
                _count += 1
        for miner_count, miner_info in _miner_info.items():
            _max_score = max(miner_info["score"])
            _maximum_score_index = miner_info["score"].index(_max_score)
            _maximum_score_uid = miner_info["index"][_maximum_score_index]
            _miner_info[miner_count]["best_submission_info"] = {
                "uid": _maximum_score_uid,
                "coldkey": miner_info["coldkey"][_maximum_score_index],
                "score": _max_score,
            }
            _final_scores[_maximum_score_uid] = _max_score
        _normalized_scores = _final_scores / np.sum(_final_scores)

        return _normalized_scores

    def _get_alpha_burn_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of scores based on alpha burn, high for more burn.
        """
        # Find owner 's hotkey
        scores = np.zeros(n_uids)
        try:
            owner_hotkey = self.metagraph.owner_hotkey

            owner_hotkey_index = self.metagraph.hotkeys.index(owner_hotkey)

            # Set alpha burn score to 1.0
            scores[owner_hotkey_index] = 1.0
        except Exception as e:
            bt.logging.error(f"Error calculating alpha burn score: {e}")
            return np.zeros(n_uids)

        bt.logging.debug(f"Alpha burn scores: {scores.tolist()}")

        return scores

    def get_onchain_scores(self, n_uids: int) -> np.ndarray:
        """
        Returns a numpy array of weighted scores combining:
        1. Challenge scores (based on performance improvements)
        2. Alpha burn scores (based on burn amount)

        Weights are defined in constants:
        - CHALLENGE_SCORES_WEIGHT (50%)
        - ALPHA_BURN_WEIGHT (50%)
        """
        # Get challenge performance scores
        challenge_scores = self._get_challenge_scores(n_uids)
        # Get alpha burn scores
        alpha_burn_scores = self._get_alpha_burn_scores(n_uids)

        # fallback if no valid submissions in any challenges
        if np.sum(challenge_scores) <= 0:
            bt.logging.info("No challenge scores, giving all weight to alpha burn")
            alpha_burn_weight = (
                constants.ALPHA_BURN_WEIGHT + constants.CHALLENGE_SCORES_WEIGHT
            )
        else:
            alpha_burn_weight = constants.ALPHA_BURN_WEIGHT

        # Combine scores using weights from constants
        final_scores = (
            challenge_scores * constants.CHALLENGE_SCORES_WEIGHT
            + alpha_burn_scores * alpha_burn_weight
        )

        bt.logging.info(f"Onchain final scores: {final_scores.tolist()}\n ")

        return final_scores
