# -*- coding: utf-8 -*-

import logging
import subprocess

from pydantic import validate_call, IPvAnyAddress, IPvAnyNetwork


logger = logging.getLogger(__name__)


@validate_call
def is_reachable(host: str, timeout: int = 3) -> bool:
    """Check if a host is reachable by pinging it.

    Args:
        host    (str, required): The host address to ping.
        timeout (int, optional): Timeout for the ping command in seconds. Defaults to 3.

    Raises:
        Exception: If there is an error while executing the ping command.

    Returns:
        bool: True if the host is reachable, False otherwise.
    """

    try:
        _cmd = ["ping", "-c", "1", "-W", str(timeout), host]
        _result = subprocess.run(
            _cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=(timeout + 1),
        )

        if _result.returncode == 0:
            return True

    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        logger.error("Not found 'ping' command on this system!")
        raise
    except Exception:
        logger.error(f"Failed to ping '{host}' host!")
        raise

    return False


@validate_call
def is_ip_in_range(ip: IPvAnyAddress, cidr: IPvAnyNetwork) -> bool:
    """Check if an IP address is within a given CIDR range.

    Args:
        ip   (IPvAnyAddress, required): IP address to check.
        cidr (IPvAnyNetwork, required): CIDR range to check against.

    Returns:
        bool: True if the IP address is within the CIDR range, False otherwise.
    """

    if ip in cidr:
        return True

    return False


__all__ = [
    "is_reachable",
    "is_ip_in_range",
]
