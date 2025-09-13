# -*- coding: utf-8 -*-

import logging
from typing import Optional

import requests
from pydantic import validate_call, SecretStr, IPvAnyAddress, IPvAnyNetwork

from api.core import utils


logger = logging.getLogger(__name__)


class Tailscale:

    _TS_API_BASE_URL = "https://api.tailscale.com/api/v2"
    _TS_CIDR = IPvAnyNetwork("100.64.0.0/10")
    _TS_RESERVED_IP_RANGES = [
        IPvAnyNetwork("100.100.0.0/24"),
        IPvAnyNetwork("100.100.100.0/24"),
        IPvAnyNetwork("100.115.92.0/23"),
    ]

    @validate_call
    def __init__(self, api_token: SecretStr, tailnet: Optional[str] = None):
        self.api_token = api_token
        if tailnet:
            self.tailnet = tailnet

    @validate_call
    def get_devices(
        self,
        tag: Optional[str] = None,
        tailnet: Optional[str] = None,
        all_fields: bool = False,
    ) -> list[dict]:
        """Get devices list from Tailscale API.

        Args:
            tag        (Optional[str], optional): Tag to filter devices. Defaults to None.
            tailnet    (Optional[str], optional): Tailnet name to filter devices. Defaults to None.
            all_fields (bool         , optional): If True, return all fields. Defaults to False.

        Raises:
            ValueError: If `tailnet` is not provided or empty.
            KeyError  : If the response from Tailscale API is not in the expected format.
            ValueError: If no devices are found in the specified tailnet.
            Exception : If there is an error while making the API request.

        Returns:
            list[dict]: List of devices in the specified tailnet, optionally filtered by tag.
        """

        _devices = []
        _tailnet = self.tailnet
        if tailnet:
            _tailnet = tailnet.strip()

        if not _tailnet:
            raise ValueError("`tailnet` attribute/argument is empty!")

        logger.debug(f"Getting devices from '{_tailnet}' tailnet...")
        try:
            _endpoint = f"/tailnet/{_tailnet}/devices"
            _query = "?fields=all" if all_fields else ""
            _url = f"{Tailscale._TS_API_BASE_URL}{_endpoint}{_query}"
            _headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_token.get_secret_value()}",
            }
            _response = requests.get(_url, headers=_headers)
            _response.raise_for_status()

            _result = _response.json()
            if not isinstance(_result, dict):
                raise KeyError("Invalid response format from Tailscale API!")

            _all_devices: list[dict] = _result.get("devices", [])
            if not _all_devices:
                raise ValueError(f"No devices found from Tailscale API!")

            if tag:
                for _device in _all_devices:
                    _tags = _device.get("tags", [])
                    if tag in _tags:
                        _devices.append(_device)
            else:
                _devices = _all_devices

            logger.debug(
                f"Successfully retrieved {len(_devices)} device(s) from '{_tailnet}' tailnet."
            )
        except Exception:
            logger.error(f"Failed to retrieve devices from '{_tailnet}' tailnet!")
            raise

        return _devices

    @validate_call
    def get_device(self, id: str, all_fields: bool = False) -> dict:
        """Get a specific device by ID from Tailscale API.

        Args:
            id         (str , required): The ID of the device to retrieve.
            all_fields (bool, optional): If True, return all fields. Defaults to False.

        Raises:
            ValueError: If `id` argument value is empty.
            KeyError  : If the response from Tailscale API is not in the expected format.
            Exception : If there is an error while making the API request.

        Returns:
            dict: Device information, including ID, name, IP address, tags, and etc.
        """

        id = id.strip()
        if not id:
            raise ValueError("`id` argument value is empty!")

        _device = {}
        logger.debug(f"Getting device with ID '{id}'...")
        try:
            _endpoint = f"/device/{id}"
            _query = "?fields=all" if all_fields else ""
            _url = f"{Tailscale._TS_API_BASE_URL}{_endpoint}{_query}"
            _headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_token.get_secret_value()}",
            }
            _response = requests.get(_url, headers=_headers)
            if _response.status_code == 404:
                logger.error(f"Not found device with '{id}' ID!")

            _response.raise_for_status()

            _device = _response.json()
            if not isinstance(_device, dict):
                raise KeyError("Invalid response format from Tailscale API!")

            logger.debug(f"Successfully retrieved device with '{id}' ID.")
        except Exception:
            logger.error(f"Failed to retrieve device with '{id}' ID!")
            raise

        return _device

    @validate_call
    def change_device_ip(self, device_id: str, ip: IPvAnyAddress) -> None:
        """Change the IP address of a specific device in Tailscale.

        Args:
            device_id (str          , required): The ID of the device to change the IP address.
            ip        (IPvAnyAddress, required): The new IP address to assign to the device.

        Raises:
            ValueError: If `device_id` argument value is empty.
            ValueError: If `ip` argument value is invalid, not within the Tailscale network range, or within reserved IP ranges.
            Exception : If there is an error while making the API request.
        """

        device_id = device_id.strip()
        if not device_id:
            raise ValueError("`device_id` argument value is empty!")

        if not utils.is_ip_in_range(ip=ip, cidr=Tailscale._TS_CIDR):
            raise ValueError(
                f"`ip` argument value '{ip}' is invalid, must be within the Tailscale network range: '{Tailscale._TS_CIDR}'!"
            )

        for _reserved_range in Tailscale._TS_RESERVED_IP_RANGES:
            if utils.is_ip_in_range(ip=ip, cidr=_reserved_range):
                raise ValueError(
                    f"`ip` argument value '{ip}' is invalid, must not be within the Tailscale reserved IP ranges: {Tailscale._TS_RESERVED_IP_RANGES}!"
                )

        logger.debug(f"Changing IP of '{device_id}' device to '{ip}'...")
        try:
            _endpoint = f"/device/{device_id}/ip"
            _url = f"{Tailscale._TS_API_BASE_URL}{_endpoint}"
            _headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_token.get_secret_value()}",
            }
            _payload = {"ipv4": str(ip)}
            _response = requests.post(_url, headers=_headers, json=_payload)
            if _response.status_code == 404:
                logger.error(f"Not found device with '{device_id}' ID!")

            _response.raise_for_status()

            logger.debug(f"Successfully changed IP of '{device_id}' device to '{ip}'.")
        except Exception as err:
            if isinstance(err, requests.RequestException):
                _message = ""
                if hasattr(err, "response") and (err.response is not None):
                    _message = err.response.text
                else:
                    _message = str(err)

                logger.error(
                    f"Failed to change IP of '{device_id}' device: {_message}!"
                )
                raise

            logger.error(f"Failed to change device IP using Tailscale API!")
            raise

        return

    ### ATTRIBUTES ###
    ## api_token ##
    @property
    def api_token(self) -> SecretStr:
        try:
            return self.__api_token
        except AttributeError:
            raise AttributeError("`api_token` attribute is not set!")

    @api_token.setter
    def api_token(self, api_token: SecretStr | str):
        if not isinstance(api_token, (SecretStr, str)):
            raise TypeError(
                f"`api_token` attribute type {type(api_token)} is invalid, must be a <SecretStr> or <str>!"
            )

        if isinstance(api_token, SecretStr):
            api_token = str(api_token.get_secret_value())

        api_token = api_token.strip()
        if not api_token:
            raise ValueError("`api_token` attribute value is empty!")

        if not api_token.startswith("tskey-api-"):
            raise ValueError(
                f"`api_token` attribute value is invalid, must start with 'tskey-api-' prefix!"
            )

        self.__api_token = SecretStr(api_token)

    ## api_token ##

    ## tailnet ##
    @property
    def tailnet(self) -> str | None:
        try:
            return self.__tailnet
        except AttributeError:
            return None

    @tailnet.setter
    def tailnet(self, tailnet: str):
        if not isinstance(tailnet, str):
            raise TypeError(
                f"`tailnet` attribute type {type(tailnet)} is invalid, must be a <str>!"
            )

        tailnet = tailnet.strip()
        if not tailnet:
            raise ValueError("`tailnet` attribute value is empty!")

        if (len(tailnet) < 2) or (128 < len(tailnet)):
            raise ValueError(
                f"`tailnet` attribute value length '{len(tailnet)}' is invalid, must be between 2 and 128 characters!"
            )

        self.__tailnet = tailnet

    ## tailnet ##
    ### ATTRIBUTES ###


__all__ = [
    "Tailscale",
]
