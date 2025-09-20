# -*- coding: utf-8 -*-

import random
from typing import Optional, List, Dict, Set
from collections import Counter, defaultdict
from itertools import combinations

import requests
from pydantic import validate_call, AnyHttpUrl, SecretStr

from api.core.configs.challenge import DevicePM, DeviceStatusEnum, DeviceStateEnum
from api.helpers.pushcut import Pushcut
from api.logger import logger
from api.config import config


class DFPManager:

    @validate_call
    def __init__(self, fp_js: str):
        self.fp_js = fp_js

    @validate_call
    def send_fp_js(
        self, request_id: str, base_url: AnyHttpUrl, api_key: SecretStr
    ) -> None:

        _endpoint = "/_fp-js"
        _base_url = str(base_url).rstrip("/")
        _url = f"{_base_url}{_endpoint}"

        logger.info(
            f"[{request_id}] - Sending fingerprinter.js file to '{_url}' DFP proxy server ..."
        )
        try:
            _headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-Key": api_key.get_secret_value(),
            }
            _payload = {"fingerprinter_js": self.fp_js}
            _response = requests.post(_url, headers=_headers, json=_payload)
            _response.raise_for_status()

            logger.info(
                f"[{request_id}] - Successfully sent fingerprinter.js file to '{_url}' DFP proxy server."
            )
        except Exception:
            logger.error(
                f"[{request_id}] - Failed to send fingerprinter.js file to '{_url}' DFP proxy server!"
            )
            raise

        return

    @validate_call
    def generate_targets(
        self, devices: list[DevicePM], n_repeat: int, random_seed: Optional[int] = None
    ) -> None:

        _target_devices = []
        for _device in devices:
            if _device.status == DeviceStatusEnum.ACTIVE:

                _pushcut = Pushcut(api_key=_device.pushcut_api_key)
                _pushcut_servers = _pushcut.get_servers()
                if not _pushcut_servers:
                    logger.warning(
                        f"Device with {{'id': {_device.id}, 'pushcut_id': '{_device.pushcut_id}'}} has no pushcut live servers, skipping..."
                    )
                    continue

                _is_pushcut_server_running = True
                for _pushcut_server in _pushcut_servers:
                    if (_pushcut_server.get("id") == _device.pushcut_server_id) and (
                        not _pushcut_server.get("isConnected", False)
                    ):
                        logger.warning(
                            f"Device with {{'id': {_device.id}, 'pushcut_id': '{_device.pushcut_id}', 'server_id': '{_device.pushcut_server_id}'}} live server is not connected, skipping..."
                        )
                        _is_pushcut_server_running = False

                if not _is_pushcut_server_running:
                    continue

                for _ in range(n_repeat):
                    _target_devices.append(
                        DevicePM(
                            **_device.model_dump(exclude={"state"}),
                            state=DeviceStateEnum.READY,
                        )
                    )

        if not _target_devices:
            raise ValueError(
                "Not found any active or connected devices to generate targets!"
            )

        if random_seed is not None:
            random.seed(random_seed)

        random.shuffle(_target_devices)

        if random_seed is not None:
            random.seed(None)

        self.target_devices = _target_devices
        return

    def score(self) -> float:
        """
        Calculate the scoring based on device fragmentation and collisions.
        Returns a score between 0.0 and 1.0.
        """
        # Extract config values
        sc_config = config.challenge.scoring
        weights = sc_config.weights
        thresholds = sc_config.thresholds

        # Aggregate data
        device_fingerprints: Dict[int, List[Optional[str]]] = defaultdict(list)
        device_models: Dict[int, Optional[str]] = {}
        fingerprint_to_devices: Dict[str, Set[int]] = defaultdict(set)

        for r in self.target_devices:
            device_fingerprints[r.id].append(r.fingerprint)
            device_models.setdefault(r.id, r.device_model)
            if r.fingerprint:
                fingerprint_to_devices[r.fingerprint].add(r.id)

        total_devices = len(device_fingerprints)
        if total_devices == 0:
            return 0.0  # Edge case: no devices

        # Calculate dynamic limits
        max_allowed_fragmented = max(
            1, round(thresholds.fragmentation.frag_pct * total_devices)
        )
        soft_collision_limit = max(
            1, round(thresholds.collision.soft_pct * total_devices)
        )
        hard_collision_limit = max(
            1, round(thresholds.collision.hard_pct * total_devices)
        )

        # Fragmentation check
        fragmented_count = 0
        for device_id, fps in device_fingerprints.items():
            total_requests = len(fps)
            if total_requests == 0 or not any(fps):
                fragmented_count += 1
                continue
            min_consistent_count = round(
                (1 - thresholds.fragmentation.inconsistency_pct) * total_requests
            )
            _, freq = Counter([fp for fp in fps if fp]).most_common(1)[0]
            if freq < min_consistent_count:
                logger.debug(
                    f"Device {device_id} is fragmented: {freq}/{total_requests} consistent fingerprints."
                )
                fragmented_count += 1

        # Collision check (group-level, one event per fingerprint)
        soft_collision_count = 0
        hard_collision_count = 0
        for fp, dev_ids in fingerprint_to_devices.items():
            num_devices_in_group = len(dev_ids)
            if num_devices_in_group < 2:
                continue

            # This represents N-1 collisions for a group of N devices.
            collision_magnitude = num_devices_in_group - 1

            models = {device_models.get(d) for d in dev_ids}

            # Soft only when all models are the same and known
            if len(models) == 1 and None not in models:
                model = next(iter(models))
                logger.debug(
                    f"Soft collision group: fingerprint {fp} on {num_devices_in_group} devices of model {model}."
                )
                soft_collision_count += collision_magnitude
            else:
                # Different models and/or unknowns present -> hard collision group
                models_str = ",".join(
                    sorted([m if m is not None else "UNKNOWN" for m in models])
                )
                logger.debug(
                    f"Hard collision group: fingerprint {fp} on {num_devices_in_group} devices across models [{models_str}]."
                )
                hard_collision_count += collision_magnitude

        # Hard fail guardrail
        if hard_collision_count > hard_collision_limit * 2:
            logger.info(
                f"Hard collision count {hard_collision_count} exceeds threshold limit {hard_collision_limit * 2}, assigning score 0."
            )
            return 0.0

        # Scoring function
        def calculate_score(count: int, limit: int, exponent: float = 1.0) -> float:
            if count > limit:
                return 0.0
            return 1.0 - (count / limit) ** exponent

        fragmentation_score = calculate_score(fragmented_count, max_allowed_fragmented)
        soft_collision_score = calculate_score(
            soft_collision_count, soft_collision_limit
        )
        hard_collision_score = calculate_score(
            hard_collision_count, hard_collision_limit, 2.0
        )

        # Total score
        total_score = (
            weights.fragmentation * fragmentation_score
            + weights.soft_collision * soft_collision_score
            + weights.hard_collision * hard_collision_score
        )

        # Optional debug output
        logger.info(f"Total devices: {total_devices}")
        logger.info(
            f"Fragmented devices: {fragmented_count}/{max_allowed_fragmented} -> {fragmentation_score:.3f}"
        )
        logger.info(
            f"Soft collisions: {soft_collision_count}/{soft_collision_limit} -> {soft_collision_score:.3f}"
        )
        logger.info(
            f"Hard collisions: {hard_collision_count}/{hard_collision_limit} -> {hard_collision_score:.3f}"
        )

        return max(0.0, min(1.0, total_score))

    ### ATTRIBUTES ###
    ## fp_js ##
    @property
    def fp_js(self) -> str:
        try:
            return self.__fp_js
        except AttributeError:
            raise AttributeError("`fp_js` attribute is not set!")

    @fp_js.setter
    def fp_js(self, fp_js: str):
        if not isinstance(fp_js, str):
            raise TypeError(
                f"`fp_js` attribute type {type(fp_js)} is invalid, must be a <str>!"
            )

        fp_js = fp_js.strip()
        if not fp_js:
            raise ValueError("`fp_js` attribute value is empty!")

        self.__fp_js = fp_js

    ## fp_js ##

    ## target_devices ##
    @property
    def target_devices(self) -> list[DevicePM]:
        try:
            return self.__target_devices
        except AttributeError:
            raise AttributeError("`target_devices` attribute is not set!")

    @target_devices.setter
    def target_devices(self, target_devices: list[DevicePM]):
        if not isinstance(target_devices, list):
            raise TypeError(
                f"`target_devices` attribute type {type(target_devices)} is invalid, must be a <list>!"
            )

        if not target_devices:
            raise ValueError("`target_devices` attribute value is empty!")

        for _task_device in target_devices:
            if not isinstance(_task_device, DevicePM):
                raise TypeError(
                    f"`target_devices` list attribute's item type {_task_device} is invalid, must be a <DevicePM>!"
                )

        self.__target_devices = target_devices

    ## target_devices ##
    ### ATTRIBUTES ###


__all__ = [
    "DFPManager",
]
