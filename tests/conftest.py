"""Fixtures for testing."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

from aiokem.main import AioKem


async def get_kem(mock_session: Mock) -> AioKem:
    """Fixture to create a mock session and authenticate."""
    mock_session.post = AsyncMock()
    mock_session.get = AsyncMock()
    kem = AioKem(session=mock_session)

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

    await kem.authenticate("username", "password")
    return kem


def load_fixture_file(fixture_file: str) -> dict[str, Any]:
    """Load fixtures from the JSON file."""
    fixtures_path = Path(__file__).parent / "fixtures" / fixture_file
    with fixtures_path.open() as f:
        return json.load(f)
