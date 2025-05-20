"""Helper functions for the aiokem package."""

from __future__ import annotations

from datetime import datetime, tzinfo
from typing import Any


def reverse_mac_address(mac: str) -> str:
    """Reverse the bytes of a MAC address."""
    # Split the MAC address into individual bytes
    mac_bytes = mac.split(":")
    # Reverse the order of the bytes
    reversed_bytes = mac_bytes[::-1]
    # Join the reversed bytes back into a MAC address string
    reversed_mac = ":".join(reversed_bytes)
    return reversed_mac


def convert_timestamp(response: dict[str, Any], key: str, tz: tzinfo) -> None:
    """Convert a timestamp in to the specified timezone."""
    value = response.get(key)
    if value:
        response[key] = datetime.fromisoformat(value).replace(tzinfo=tz).isoformat()
