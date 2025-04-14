"""AioKem class for interacting with Kohler Energy Management System (KEM) API."""

from typing import Any

from aiohttp import ClientSession, ClientTimeout
from multidict import CIMultiDict

AUTHENTICATION_URL = "https://kohler-homeenergy.okta.com/oauth2/default/v1/token"
CLIENT_KEY = (
    "MG9hMXFpY3BkYWdLaXdFekYxZDg6d3Raa1FwNlY1T09vMW9"
    "PcjhlSFJHTnFBWEY3azZJaXhtWGhINHZjcnU2TWwxSnRLUE5obXdsMEN1MGlnQkVIRg=="
)
API_KEY = "pgH7QzFHJx4w46fI~5Uzi4RvtTwlEXp"
API_BASE = (
    "https://az-amer-prod-hems-capp.jollyglacier-72224ec0.eastus.azurecontainerapps.io"
)


class AioKem:
    """AioKem class for interacting with Kohler Energy Management System (KEM) API."""

    def __init__(self, session: ClientSession = None) -> None:
        """Initialize the AioKem class."""
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._session = (
            session if session else ClientSession(timeout=ClientTimeout(total=10))
        )

    async def login(self, username: str, password: str) -> None:
        """Login to the server."""
        headers = CIMultiDict(
            {
                "accept": "application/json",
                "authorization": f"Basic {CLIENT_KEY}",
                "content-type": "application/x-www-form-urlencoded",
            }
        )

        data = {
            "grant_type": "password",
            "username": username,
            "password": password,  # Replace 'pass' with the actual password
            "scope": "openid profile offline_access email",
        }

        response = await self._session.post(
            AUTHENTICATION_URL, headers=headers, data=data
        )
        response_data = await response.json()
        if response.status != 200:
            raise Exception(
                f"Login failed: {response_data.get('error_description', 'unknown')}"
            )
        self._token = response_data.get("access_token")
        self._refresh_token = response_data.get("refresh_token")
        if not self._token:
            raise Exception("Login failed: No access token received")
        if not self._refresh_token:
            raise Exception("Login failed: No refresh token received")

    async def get_homes(self) -> list[dict[str, Any]]:
        """Get the list of homes."""
        url = f"{API_BASE}/kem/api/v3/homeowner/homes"
        headers = {
            "apikey": API_KEY,
            "authorization": f"bearer {self._token}",
        }

        response = await self._session.get(url, headers=headers)
        if response.status != 200:
            raise Exception(f"Failed to fetch homes: {response.status}")
        response_data = await response.json()
        if not response_data:
            raise Exception("No data received")
        return response_data

    async def get_generator_data(self, generator_id: int) -> dict[str, Any]:
        """Get generator data for a specific generator."""
        url = f"{API_BASE}/kem/api/v3/devices/{generator_id}"
        headers = {
            "apikey": API_KEY,
            "authorization": f"bearer {self._token}",
        }

        response = await self._session.get(url, headers=headers)
        if response.status != 200:
            raise Exception(f"Failed to fetch generator data: {response.status}")
        response_data = await response.json()
        if not response_data:
            raise Exception("No data received")
        return response_data

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()
