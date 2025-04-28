"""AioKem class for interacting with Kohler Energy Management System (KEM) API."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

import jwt
from aiohttp import (
    ClientConnectionError,
    ClientConnectorError,
    ClientSession,
    ClientTimeout,
    hdrs,
)
from multidict import CIMultiDict, istr
from yarl import URL

from .exceptions import (
    AuthenticationCredentialsError,
    AuthenticationError,
    CommunicationError,
    ServerError,
)
from .message_logger import log_json_message

_LOGGER = logging.getLogger(__name__)

AUTHENTICATION_URL = URL("https://kohler-homeenergy.okta.com/oauth2/default/v1/token")
CLIENT_KEY = (
    "MG9hMXFpY3BkYWdLaXdFekYxZDg6d3Raa1FwNlY1T09vMW9"
    "PcjhlSFJHTnFBWEY3azZJaXhtWGhINHZjcnU2TWwxSnRLUE5obXdsMEN1MGlnQkVIRg=="
)
API_KEY = "pgH7QzFHJx4w46fI~5Uzi4RvtTwlEXp"
API_KEY_HDR = istr("apikey")
API_BASE = "https://api.hems.rehlko.com"
API_BASE_URL = URL(API_BASE)
HOMES_URL = URL(f"{API_BASE}/kem/api/v3/homeowner/homes")

AUTH_HEADERS = CIMultiDict(
    {
        hdrs.ACCEPT: "application/json",
        hdrs.AUTHORIZATION: f"Basic {CLIENT_KEY}",
        hdrs.CONTENT_TYPE: "application/x-www-form-urlencoded",
    }
)
CLIENT_TIMEOUT = ClientTimeout(total=10)

RETRY_EXCEPTIONS = (
    CommunicationError,
    ServerError,
    ClientConnectorError,
)

AUTHORIZATION_EXCEPTIONS = (AuthenticationError,)


class AioKem:
    """AioKem class for interacting with Kohler Energy Management System (KEM) API."""

    def __init__(self, session: ClientSession) -> None:
        """
        Initialize the AioKem class.

        Args:
            session (ClientSession): An aiohttp ClientSession object.

        """
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._session = session
        self._token_expires_at: float = 0
        self._token_expires_in: int = 0
        self._retry_count: int = 0
        self._retry_delays: list[int] = []
        self._refresh_lock = asyncio.Lock()

    def set_retry_policy(self, retry_count: int, retry_delays: list[int]) -> None:
        """
        Set the retry policy for the session.

        Args:
            retry_count (int): Number of retries. Zero means no retries.
            retry_delays (list[int]): Delay between retries in seconds for each retry.

        """
        self._retry_count = retry_count
        self._retry_delays = retry_delays

    async def on_refresh_token_update(self, refresh_token: str | None) -> None:
        """Callback for refresh token update."""
        # This method can be overridden to handle refresh token updates
        _LOGGER.debug("Refresh token updated: %s", refresh_token)

    async def _authentication_helper(self, data: dict[str, Any]) -> None:
        """Helper function for authentication."""
        _LOGGER.debug("Sending authentication request to %s", AUTHENTICATION_URL)
        try:
            response = await self._session.post(
                AUTHENTICATION_URL, headers=AUTH_HEADERS, data=data
            )
            response_data = await response.json()
        except ClientConnectionError as e:
            raise CommunicationError(f"Connection error: {e}") from e

        if _LOGGER.isEnabledFor(logging.DEBUG):
            log_json_message(response_data)

        if response.status != HTTPStatus.OK:
            if response.status == HTTPStatus.BAD_REQUEST:
                raise AuthenticationCredentialsError(
                    f"Invalid Credentials: "
                    f"{response_data.get('error_description', 'unknown')} "
                    f"Code {response.status}"
                )
            else:
                raise AuthenticationError(
                    f"Authentication failed: "
                    f"{response_data.get('error_description', 'unknown')} "
                    f"Code {response.status}"
                )
        self._token = response_data.get("access_token")
        if not self._token:
            raise ServerError("Login failed: No access token received")

        self._refresh_token = response_data.get("refresh_token")
        if not self._refresh_token:
            raise ServerError("Login failed: No refresh token received")

        self._token_expires_in = response_data.get("expires_in")
        self._token_expires_at = time.monotonic() + self._token_expires_in
        _LOGGER.debug(
            "Authentication successful. Token expires at %s",
            datetime.now() + timedelta(seconds=self._token_expires_in),
        )

    async def authenticate(
        self, email: str, password: str, refresh_token: str | None = None
    ) -> None:
        """Login to the server."""
        _LOGGER.debug("Authenticating user %s", email)
        self.email = email
        self.password = password
        if refresh_token:
            with contextlib.suppress(AuthenticationError):
                await self.authenticate_with_refresh_token(refresh_token)
                return
        await self._authentication_helper(
            {
                "grant_type": "password",
                "username": email,
                "password": password,
                "scope": "openid profile offline_access email",
            }
        )
        await self.on_refresh_token_update(self._refresh_token)

    async def authenticate_with_refresh_token(self, refresh_token: str) -> None:
        """Login to the server using a refresh token."""
        _LOGGER.debug("Authenticating with refresh token.")
        await self._authentication_helper(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "openid profile offline_access email",
            }
        )
        await self.on_refresh_token_update(self._refresh_token)

    async def check_and_refresh_token(self) -> None:
        """Check if the token is expired and refresh it if necessary."""
        _LOGGER.debug("Checking if token needs to be refreshed.")
        if not self._token:
            raise AuthenticationError("Not authenticated")
        if time.monotonic() >= self._token_expires_at:
            # Prevent reentry and refreshing token multiple times
            async with self._refresh_lock:
                if time.monotonic() >= self._token_expires_at:
                    _LOGGER.debug("Access token expired. Refreshing token.")
                await self._authentication_helper(
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                        "scope": "openid profile offline_access email",
                    }
                )
            # Execute callback outside of lock to avoid deadlock
            await self.on_refresh_token_update(self._refresh_token)

    async def _get_helper(self, url: URL) -> dict[str, Any] | list[dict[str, Any]]:
        """Helper function to get data from the API."""
        headers = CIMultiDict(
            {
                API_KEY_HDR: API_KEY,
                hdrs.AUTHORIZATION: f"bearer {self._token}",
            }
        )
        _LOGGER.debug("Sending GET request to %s", url)
        try:
            response = await self._session.get(url, headers=headers)
            response_data = await response.json()
        except ClientConnectionError as e:
            raise CommunicationError(f"Connection error: {e}") from e

        if _LOGGER.isEnabledFor(logging.DEBUG):
            log_json_message(response_data)

        if response.status != 200:
            if response.status == HTTPStatus.UNAUTHORIZED:
                raise AuthenticationError(f"Unauthorized: {response_data}")
            elif response.status == HTTPStatus.INTERNAL_SERVER_ERROR:
                raise ServerError(
                    f"Server error: {response_data.get('error_description', 'unknown')}"
                )
            else:
                raise CommunicationError(
                    f"Failed to fetch data: {response.status} {response_data}"
                )
        _LOGGER.debug("Data successfully fetched from %s", url)
        return response_data

    async def _retry_auth(self) -> bool:
        """Retry authentication."""
        _LOGGER.debug("Retrying authentication")
        try:
            await self.authenticate(email=self.email, password=self.password)
        except AuthenticationError as error:
            _LOGGER.error("Authentication failed: %s", error)
            return False
        return True

    async def _retry_get_helper(
        self, url: URL
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Retry GET request with exponential backoff."""
        await self.check_and_refresh_token()
        for attempt in range(self._retry_count + 1):
            if attempt > 0:
                await asyncio.sleep(self._retry_delays[attempt - 1])
            try:
                return await self._get_helper(url)
            except RETRY_EXCEPTIONS as error:
                _LOGGER.warning("Error communicating with KEM: %s", error)
            except AUTHORIZATION_EXCEPTIONS as error:
                _LOGGER.warning("Authorization error communicating with KEM: %s", error)
                if not await self._retry_auth():
                    raise AuthenticationError("Retry authentication failed") from error
        _LOGGER.error("Failed to get data after %s retries", attempt)
        raise CommunicationError("Failed to get data after retries")

    async def get_homes(self) -> list[dict[str, Any]]:
        """Get the list of homes."""
        _LOGGER.debug("Fetching list of homes.")
        response = await self._retry_get_helper(HOMES_URL)
        if not isinstance(response, list):
            raise TypeError(
                f"Expected a list of homes, but got a different type {type(response)}"
            )
        return response

    async def get_generator_data(self, generator_id: int) -> dict[str, Any]:
        """Get generator data for a specific generator."""
        _LOGGER.debug("Fetching generator data for generator ID %d", generator_id)
        url = API_BASE_URL.with_path(f"/kem/api/v3/devices/{generator_id}")
        response = await self._retry_get_helper(url)
        if not isinstance(response, dict):
            raise TypeError(
                "Expected a dictionary for generator data, "
                f"but got a different type {type(response)}"
            )
        return response

    async def close(self) -> None:
        """Close the session."""
        _LOGGER.debug("Closing AioKem.")
        self._session = None
        self._token = None
        self._refresh_token = None

    def get_token_subject(self) -> str | None:
        """Returns the subject of the JWT token, used as unique id for the user."""
        if not self._token:
            raise AuthenticationError("Not authenticated")
        # Decode the JWT token and extract the subject
        try:
            token_data = jwt.decode(self._token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            _LOGGER.error("Failed to decode JWT token: %s", e)
            return None
        return token_data.get("sub", None)
