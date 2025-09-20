# -*- coding: utf-8 -*-

import requests
from pydantic import validate_call

from api.core.constants import ErrorCodeEnum
from api.core import utils
from api.core.configs.challenge import DeviceStatusEnum
from api.core.exceptions import BaseHTTPException
from api.config import config
from api.logger import logger


@validate_call
def check_health(request_id: str) -> dict:

    _base_response = {
        "message": "Everything is OK.",
        "status": "OK",
        "data": {
            "checks": {
                "challenger-api": {
                    "status": "OK",
                    "message": "Challenger API is up and running.",
                }
            }
        },
    }

    _base_url = str(config.challenge.proxy_inter_base_url).rstrip("/")
    _endpoint = "/health"
    _url = f"{_base_url}{_endpoint}"
    _query_params = "?" if config.challenge.devices else ""
    for _device in config.challenge.devices:
        if _device.status == DeviceStatusEnum.ACTIVE:
            _query_params += f"device_ips={_device.ts_ip}&"
    _query_params = _query_params.rstrip("&")
    _url += _query_params

    logger.info(
        f"[{request_id}] - Checking health of DFP proxy server and devices with URL '{_url}'..."
    )
    _headers = {
        "Accept": "application/json",
        "X-API-Key": config.challenge.api_key.get_secret_value(),
    }
    _response = None
    try:
        _response = requests.get(_url, headers=_headers)
        try:
            _response_json = _response.json()
        except ValueError as e:
            _response_json = utils.deep_merge(
                _base_response,
                {
                    "message": "Invalid JSON response from DFP Proxy server.",
                    "status": "UNHEALTHY",
                    "error": e,
                },
            )
    except requests.exceptions.RequestException as e:
        # No response object at all
        _response_json = utils.deep_merge(
            _base_response,
            {
                "message": "Request to DFP Proxy failed.",
                "status": "UNHEALTHY",
                "error": e,
            },
        )

        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.SERVICE_UNAVAILABLE,
            message="DFP Proxy server is not reachable!",
            detail=_response_json,
        )

    if _response is not None and _response.status_code == 503:
        logger.error(
            f"DFP Proxy server or some devices are not reachable: {_response.text}"
        )
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.SERVICE_UNAVAILABLE,
            message="DFP Proxy server or some devices are not reachable!",
            detail=_response_json,
        )

    _response_json = utils.deep_merge(_base_response, _response_json)
    _response.raise_for_status()
    logger.success(
        f"[{request_id}] - Successfully checked health of DFP proxy server and devices with URL '{_url}'."
    )

    return _response_json


__all__ = [
    "check_health",
]
