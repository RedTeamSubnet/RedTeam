# -*- coding: utf-8 -*-

import time

from pydantic import validate_call
from api.core.configs.challenge import DeviceStateEnum
from api.core.services import utils as utils_services
from api.config import config
from api.helpers.tailscale import Tailscale
from api.helpers.pushcut import Pushcut
from api.logger import logger

from .schemas import MinerInput, MinerOutput
from .dfp import DFPManager


tailscale = Tailscale(
    api_token=config.challenge.ts_api_token, tailnet=config.challenge.ts_tailnet
)
pushcut = Pushcut(api_key=config.challenge.pushcut_api_key)

dfp_manager: DFPManager


def get_task() -> MinerInput:
    """Return a new challenge task."""
    return MinerInput()


@validate_call
def score(request_id: str, miner_output: MinerOutput) -> float:

    global dfp_manager
    _score = 0.0

    # Removed ESLint check here
    dfp_manager = DFPManager(fp_js=miner_output.fingerprinter_js)
    dfp_manager.send_fp_js(
        request_id=request_id,
        base_url=config.challenge.proxy_inter_base_url,
        api_key=config.challenge.api_key,
    )
    utils_services.check_health(request_id=request_id)
    dfp_manager.generate_targets(
        devices=config.challenge.devices,
        n_repeat=config.challenge.n_repeat,
        random_seed=config.challenge.random_seed,
    )

    for _i, _target_device in enumerate(dfp_manager.target_devices):
        if config.challenge.change_ts_ip:
            tailscale.change_device_ip(
                device_id=_target_device.ts_node_id, ip=config.challenge.ts_static_ip
            )
            time.sleep(1)

        _web_endpoint = "/_web"
        _web_base_url = str(config.challenge.proxy_exter_base_url).rstrip("/")
        _web_url = f"{_web_base_url}{_web_endpoint}?order_id={_i}"
        logger.info(
            f"[{request_id}] - Executing input '{_web_url}' URL for device with {{'order_id': {_i}, 'id': {_target_device.id}}} ..."
        )
        _target_device.state = DeviceStateEnum.RUNNING
        success = pushcut.execute(
            shortcut=config.challenge.pushcut_shortcut,
            input_url=_web_url,
            timeout=config.challenge.pushcut_timeout,
            server_id=_target_device.pushcut_server_id,
            api_key=_target_device.pushcut_api_key,
            raise_on_error=False,  # Don't raise exception, just return False
        )

        if not success:
            _target_device.state = DeviceStateEnum.ERROR
            logger.error(
                f"[{request_id}] - Could not execute pushcut for device with {{'order_id': {_i}, 'id': {_target_device.id}}} (server unavailable or request failed)"
            )
            logger.debug(
                f"[{request_id}] - Device {{'order_id': {_i}, 'id': {_target_device.id}}} marked as ERROR and will be excluded from scoring. No request sent to external proxy."
            )
            continue

        logger.info(
            f"[{request_id}] - Successfully executed input '{_web_url}' URL for device with {{'order_id': {_i}, 'id': {_target_device.id}}}."
        )

        _t = 0
        while True:
            if _target_device.state == DeviceStateEnum.COMPLETED:
                logger.success(
                    f"[{request_id}] - Successfully completed fingerprinting for device with {{'order_id': {_i}, 'id': {_target_device.id}, 'fingerprint': '{_target_device.fingerprint}'}}."
                )
                break

            if config.challenge.fp_timeout <= _t:
                logger.warning(
                    f"[{request_id}] - Device with {{'order_id': {_i}, 'id': {_target_device.id}}} could not completed fingerprinting within {config.challenge.fp_timeout} seconds!"
                )
                _target_device.state = DeviceStateEnum.TIMEOUT
                break

            _t = _t + 1
            time.sleep(1)

        if config.challenge.change_ts_ip:
            tailscale.change_device_ip(
                device_id=_target_device.ts_node_id, ip=_target_device.ts_ip
            )

    _score = dfp_manager.score()
    return _score


@validate_call
def set_fingerprint(order_id: int, fingerprint: str) -> None:

    global dfp_manager

    if not dfp_manager:
        raise RuntimeError(
            "'dfp_manager' is not initialized, please run '/score' endpoint first!"
        )

    if len(dfp_manager.target_devices) <= order_id:
        raise IndexError(f"Order ID {order_id} is out of range!")

    _target_device = dfp_manager.target_devices[order_id]
    if _target_device.state == DeviceStateEnum.COMPLETED:
        raise ValueError(
            f"Device with {{'id': {_target_device.id}, 'order_id': {order_id}}} already completed fingerprinting!"
        )

    _target_device.fingerprint = fingerprint.strip()
    _target_device.state = DeviceStateEnum.COMPLETED

    return


__all__ = [
    "get_task",
    "score",
    "set_fingerprint",
]
