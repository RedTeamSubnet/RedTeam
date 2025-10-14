# -*- coding: utf-8 -*-

import logging
from typing import Optional

import requests
from pydantic import validate_call, SecretStr, AnyHttpUrl


logger = logging.getLogger(__name__)


class Pushcut:

    _PUSHCUT_API_V1_BASE_URL = "https://api.pushcut.io/v1"
    _PUSHCUT_API_V2_BASE_URL = "https://api.pushcut.io/v2"

    @validate_call
    def __init__(self, api_key: SecretStr):
        self.api_key = api_key

    @validate_call
    def get_devices(self) -> list[dict]:
        """Get devices list from Pushcut.io API.

        Raises:
            KeyError  : If the response from Pushcut.io API is not in the expected format.
            ValueError: If no devices are found from Pushcut.io API.
            Exception : If there is an error while making the API request.

        Returns:
            list[dict]: List of devices from Pushcut.io API.
        """

        _devices = []
        logger.debug("Getting devices from Pushcut.io API...")
        try:
            _endpoint = "/devices"
            _url = f"{Pushcut._PUSHCUT_API_V1_BASE_URL}{_endpoint}"
            _headers = {
                "Content-Type": "application/json",
                "API-Key": self.api_key.get_secret_value(),
            }

            response = requests.get(_url, headers=_headers)
            response.raise_for_status()

            _devices: list[dict] = response.json()
            if not isinstance(_devices, list):
                raise KeyError("Invalid response format from Pushcut.io API!")

            if not _devices:
                raise ValueError("No devices found from Pushcut.io API!")

            logger.debug(
                f"Successfully retrieved {len(_devices)} device(s) from Pushcut.io API."
            )
        except Exception:
            logger.error(f"Failed to retrieve devices from Pushcut.io API!")
            raise

        return _devices

    @validate_call
    def get_servers(self) -> list[dict]:
        """Get live device servers list from Pushcut.io API.

        Raises:
            KeyError  : If the response from Pushcut.io API is not in the expected format.
            ValueError: If no servers are found from Pushcut.io API.
            Exception : If there is an error while making the API request.

        Returns:
            list[dict]: List of live device servers from Pushcut.io API.
        """

        _servers = []
        logger.debug("Getting servers from Pushcut.io API...")
        try:
            _endpoint = "/servers"
            _url = f"{Pushcut._PUSHCUT_API_V2_BASE_URL}{_endpoint}"
            _headers = {
                "Content-Type": "application/json",
                "API-Key": self.api_key.get_secret_value(),
            }

            response = requests.get(_url, headers=_headers)
            response.raise_for_status()

            _servers: list[dict] = response.json()
            if not isinstance(_servers, list):
                raise KeyError("Invalid response format from Pushcut.io API!")

            if not _servers:
                raise ValueError("No servers found from Pushcut.io API!")

            logger.debug(
                f"Successfully retrieved {len(_servers)} server(s) from Pushcut.io API."
            )
        except Exception:
            logger.error(f"Failed to retrieve servers from Pushcut.io API!")
            raise

        return _servers

    @validate_call
    def execute(
        self,
        shortcut: str,
        input_url: AnyHttpUrl,
        timeout: int | str | None = None,
        delay: Optional[str] = None,
        identifier: Optional[str] = None,
        server_id: Optional[str] = None,
        api_key: Optional[SecretStr] = None,
    ) -> None:
        """Execute a shortcut on Pushcut.io with the provided input URL.

        Args:
            shortcut    (str                , required): The name of the shortcut to execute.
            input_url   (AnyHttpUrl         , required): The input URL to pass to the shortcut.
            timeout     (int | str | None.  , optional): Timeout for the execution in seconds, or 'nowait' for no wait asynchronous execution. Defaults to None.
            delay       (Optional[str]      , optional): Delay before execution in seconds. Defaults to None.
            indentifier (Optional[str]      , optional): For delayed execution, an identifier for the execution. Defaults to None.
            server_id   (Optional[str]      , optional): The ID of the server to execute the shortcut on. Defaults to None.
            api_key     (Optional[SecretStr], optional): The API key for Pushcut.io. Defaults to None.

        Raises:
            ValueError: If `shortcut` argument value is empty.
            Exception : If there is an error while executing the shortcut on Pushcut.io.
        """

        shortcut = shortcut.strip()
        if not shortcut:
            raise ValueError("`shortcut` argument value is empty!")

        _api_key = self.api_key
        if api_key:
            _api_key = api_key

        logger.debug(
            f"Executing '{shortcut}' shortcut with '{input_url}' input URL on Pushcut.io..."
        )
        try:
            _endpoint = "/execute"
            _url = f"{Pushcut._PUSHCUT_API_V1_BASE_URL}{_endpoint}"
            _headers = {
                "Content-Type": "application/json",
                "API-Key": _api_key.get_secret_value(),
            }

            _payload = {"shortcut": shortcut, "input": str(input_url)}
            if timeout:
                _payload["timeout"] = str(timeout)

            if delay:
                _payload["delay"] = delay

            if identifier:
                _payload["identifier"] = identifier

            if server_id:
                _payload["serverId"] = server_id

            response = requests.post(_url, headers=_headers, json=_payload)
            response.raise_for_status()

            logger.debug(
                f"Successfully executed '{shortcut}' shortcut with '{input_url}' input URL on Pushcut.io!"
            )
        except Exception:
            logger.error(
                f"Failed to execute '{shortcut}' shortcut with '{input_url}' input URL on Pushcut.io!"
            )
            raise

        return

    ### ATTRIBUTES ###
    ## api_key ##
    @property
    def api_key(self) -> SecretStr:
        try:
            return self.__api_key
        except AttributeError:
            raise AttributeError("`api_key` attribute is not set!")

    @api_key.setter
    def api_key(self, api_key: SecretStr | str):
        if not isinstance(api_key, (SecretStr, str)):
            raise TypeError(
                f"`api_key` attribute type {type(api_key)} is invalid, must be a <SecretStr> or <str>!"
            )

        if isinstance(api_key, SecretStr):
            api_key = str(api_key.get_secret_value())

        api_key = api_key.strip()
        if not api_key:
            raise ValueError("`api_key` attribute value is empty!")

        self.__api_key = SecretStr(api_key)

    ## api_key ##
    ### ATTRIBUTES ###


__all__ = [
    "Pushcut",
]
