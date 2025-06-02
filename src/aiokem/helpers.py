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
    """Convert a timestamp that does not have a tz in to the specified timezone."""
    value = response.get(key)
    if value:
        dt = datetime.fromisoformat(value)
        # Different controllers can return timestamps with or without tzinfo
        # If tzinfo is None, we need to set it to the provided tz
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        response[key] = dt.isoformat()


def convert_number_abs(response: dict[str, Any], key: str) -> None:
    """Convert a number to its absolute value."""
    value = response.get(key)
    if value is not None:
        response[key] = abs(value)
