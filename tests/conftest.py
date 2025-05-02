"""Fixtures for testing."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from aiokem.main import AioKem


class MyAioKem(AioKem):
    """Test class for AioKem."""

    def __init__(self, session: Mock) -> None:
        super().__init__(session=session)
        self.refreshed = False
        self.refreshed_token: str | None = None
        self.set_refresh_token_callback(self.refresh_token_update)

    async def refresh_token_update(self, refresh_token: str | None) -> None:
        """Override the refresh token update method."""
        self.refreshed = True
        self.refreshed_token = refresh_token


async def get_kem(mock_session: Mock) -> AioKem:
    """Fixture to create a mock session and authenticate."""
    mock_session.post = AsyncMock()
    mock_session.get = AsyncMock()
    kem = MyAioKem(session=mock_session)

    # Mock the response for the login method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "token_type": "Bearer",
        "expires_in": 3600,
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
    }
    mock_session.post.return_value = mock_response

    await kem.authenticate("email", "password")
    return kem


def load_fixture_file(fixture_file: str) -> dict[str, Any]:
    """Load fixtures from the JSON file."""
    fixtures_path = Path(__file__).parent / "fixtures" / fixture_file
    with fixtures_path.open() as f:
        return json.load(f)


@pytest.fixture()
def generator_data() -> dict[str, Any]:
    """Fixture for generator data."""
    return load_fixture_file("generator_data.json")


@pytest.fixture()
def mock_session() -> Mock:
    """Fixture for a mock session."""
    return Mock()
