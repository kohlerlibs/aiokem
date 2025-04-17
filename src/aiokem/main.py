"""AioKem class for interacting with Kohler Energy Management System (KEM) API."""

import logging
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

from aiohttp import ClientConnectionError, ClientSession, ClientTimeout
from multidict import CIMultiDict
from yarl import URL

from .exceptions import (
    AuthenticationCredentialsError,
    AuthenticationError,
    CommunicationError,
    ServerError,
)

_LOGGER = logging.getLogger(__name__)

AUTHENTICATION_URL = URL("https://kohler-homeenergy.okta.com/oauth2/default/v1/token")
CLIENT_KEY = (
    "MG9hMXFpY3BkYWdLaXdFekYxZDg6d3Raa1FwNlY1T09vMW9"
    "PcjhlSFJHTnFBWEY3azZJaXhtWGhINHZjcnU2TWwxSnRLUE5obXdsMEN1MGlnQkVIRg=="
)
API_KEY = "pgH7QzFHJx4w46fI~5Uzi4RvtTwlEXp"

API_BASE = (
    "https://az-amer-prod-hems-capp.jollyglacier-72224ec0.eastus.azurecontainerapps.io"
)
HOMES_URL = URL(f"{API_BASE}/kem/api/v3/homeowner/homes")


class AioKem:
    """AioKem class for interacting with Kohler Energy Management System (KEM) API."""

    def __init__(self, session: ClientSession = None) -> None:
        """Initialize the AioKem class."""
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._session = (
            session if session else ClientSession(timeout=ClientTimeout(total=10))
        )
        _LOGGER.info("AioKem instance initialized.")

    async def _authentication_helper(
        self, headers: CIMultiDict, data: CIMultiDict
    ) -> None:
        try:
            _LOGGER.debug("Sending authentication request to %s", AUTHENTICATION_URL)
            response = await self._session.post(
                AUTHENTICATION_URL, headers=headers, data=data
            )
            response_data = await response.json()
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
                raise Exception("Login failed: No access token received")

            self._refresh_token = response_data.get("refresh_token")
            if not self._refresh_token:
                raise Exception("Login failed: No refresh token received")

            self._token_expiration = response_data.get("expires_in")
            self._token_expires_at = datetime.now() + timedelta(
                seconds=self._token_expiration
            )
            _LOGGER.info(
                "Authentication successful. Token expires at %s", self._token_expires_at
            )

        except ClientConnectionError as e:
            raise CommunicationError(f"Connection error: {e}") from e

    async def authenticate(self, username: str, password: str) -> None:
        """Login to the server."""
        _LOGGER.info("Authenticating user %s", username)
        headers = CIMultiDict(
            {
                "accept": "application/json",
                "authorization": f"Basic {CLIENT_KEY}",
                "content-type": "application/x-www-form-urlencoded",
            }
        )

        data = CIMultiDict(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
                "scope": "openid profile offline_access email",
            }
        )

        await self._authentication_helper(headers, data)

    async def refresh_token(self) -> None:
        """Refresh the access token using the refresh token."""
        _LOGGER.info("Refreshing access token.")
        if not self._refresh_token:
            raise AuthenticationError("No refresh token available")

        headers = CIMultiDict(
            {
                "accept": "application/json",
                "authorization": f"Basic {CLIENT_KEY}",
                "content-type": "application/x-www-form-urlencoded",
            }
        )

        data = CIMultiDict(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "scope": "openid profile offline_access email",
            }
        )
        await self._authentication_helper(headers, data)

    async def _get_helper(self, url: URL) -> dict[str, Any] | list[dict[str, Any]]:
        """Helper function to get data from the API."""
        if not self._token:
            raise AuthenticationError("Not authenticated")
        if datetime.now() >= self._token_expires_at:
            _LOGGER.info("Access token expired. Refreshing token.")
            await self.refresh_token()

        headers = CIMultiDict(
            {
                "apikey": API_KEY,
                "authorization": f"bearer {self._token}",
            }
        )

        try:
            _LOGGER.debug("Sending GET request to %s", url)
            response = await self._session.get(url, headers=headers)
            response_data = await response.json()
            if response.status != 200:
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise AuthenticationError(f"Unauthorized: {response_data}")
                elif response.status == HTTPStatus.INTERNAL_SERVER_ERROR:
                    raise ServerError(
                        "Server error: "
                        f"{response_data.get('error_description', 'unknown')}"
                    )
                else:
                    raise CommunicationError(
                        f"Failed to fetch data: {response.status} {response_data}"
                    )

        except ClientConnectionError as e:
            raise CommunicationError(f"Connection error: {e}") from e

        _LOGGER.info("Data successfully fetched from %s", url)
        return response_data

    async def get_homes(self) -> list[dict[str, Any]]:
        """Get the list of homes."""
        _LOGGER.info("Fetching list of homes.")
        response = await self._get_helper(HOMES_URL)
        if not isinstance(response, list):
            raise TypeError(
                f"Expected a list of homes, but got a different type {type(response)}"
            )
        return response

    async def get_generator_data(self, generator_id: int) -> dict[str, Any]:
        """Get generator data for a specific generator."""
        _LOGGER.info("Fetching generator data for generator ID %d", generator_id)
        url = URL(f"{API_BASE}/kem/api/v3/devices/{generator_id}")
        response = await self._get_helper(url)
        if not isinstance(response, dict):
            raise TypeError(
                "Expected a dictionary for generator data, "
                f"but got a different type {type(response)}"
            )
        return response

    async def close(self) -> None:
        """Close the session."""
        _LOGGER.info("Closing the session.")
        await self._session.close()
