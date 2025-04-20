"""Module to log messages to files."""
# pylint: disable=line-too-long

from __future__ import annotations

import copy
import json
import logging
from typing import Any

REDACTED: str = "**redacted**"

_LOGGER = logging.getLogger(__name__)

redacted_fields = [
    "lat",
    "long",
    "address1",
    "address2",
    "city",
    "state",
    "country",
    "postalCode",
    "serialNumber",
    "deviceIpAddress",
    "macAddress",
    "businessPartnerNo",
    "e164PhoneNumber",
    "displayPhoneNumber",
    "adminEmails",
    "associatedUsers",
    "access_token",
    "refresh_token",
    "id_token",
]


def redact_fields(log_message: Any) -> Any:
    """Removes redacted fields from messages."""
    # This can be optimized, but for now, it works and has a test.
    if isinstance(log_message, dict):
        for k, v in log_message.items():
            if isinstance(v, dict):
                log_message[k] = redact_fields(v)
            elif isinstance(v, list):
                log_message[k] = [redact_fields(i) for i in v]
        for field in redacted_fields:
            if field in log_message:
                log_message[field] = REDACTED
    elif isinstance(log_message, list):
        for i in range(len(log_message)):
            if isinstance(log_message[i], dict):
                log_message[i] = redact_fields(log_message[i])
            elif isinstance(log_message[i], list):
                log_message[i] = [redact_fields(j) for j in log_message[i]]
            for field in redacted_fields:
                if field in log_message[i]:
                    log_message[i][field] = REDACTED
    return log_message


def log_json_message(json_message: dict[str, Any] | list[dict[str, Any]]) -> None:
    """Logs a JSON message redacting sensitive information."""
    if not json_message:
        _LOGGER.debug("No JSON message to log")
        return
    log_message = redact_fields(copy.deepcopy(json_message))
    _LOGGER.debug(json.dumps(log_message, indent=4))
