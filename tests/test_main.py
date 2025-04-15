import json
from http import HTTPStatus
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientConnectionError

from aiokem.exceptions import (
    AuthenticationCredentialsError,
    AuthenticationError,
    CommunicationError,
)
from aiokem.main import API_BASE, API_KEY, AUTHENTICATION_URL, HOMES_URL, AioKem


@pytest.mark.asyncio
async def test_login():
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = AioKem(session=mock_session)

    # Mock the response for the login method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
    }
    mock_session.post.return_value = mock_response

    # Call the login method
    await kem.login("username", "password")

    # Assert that the access token and refresh token are set correctly
    assert kem._token == "mock_access_token"  # noqa: S105
    assert kem._refresh_token == "mock_refresh_token"  # noqa: S105
    # Assert that the session.post method was called with the correct URL and data
    mock_session.post.assert_called_once()
    assert mock_session.post.call_args[0][0] == AUTHENTICATION_URL
    assert mock_session.post.call_args[1]["data"] == {
        "grant_type": "password",
        "username": "username",
        "password": "password",
        "scope": "openid profile offline_access email",
    }


@pytest.mark.asyncio
async def test_login_exceptions():
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = AioKem(session=mock_session)

    # Mock the response for the login method
    mock_response = AsyncMock()
    mock_response.status = HTTPStatus.BAD_REQUEST
    mock_response.json.return_value = {
        "error_description": "The credentials provided were invalid.",
    }
    mock_session.post.return_value = mock_response

    # Call the login method
    with pytest.raises(AuthenticationCredentialsError) as excinfo:
        await kem.login("username", "password")

    # Assert that the access token and refresh token are set correctly
    assert kem._token is None
    assert kem._refresh_token is None
    # Assert that the exception message is correct
    assert (
        str(excinfo.value)
        == "Invalid Credentials: The credentials provided were invalid. Code 400"
    )

    mock_response = AsyncMock()
    mock_response.status = HTTPStatus.FORBIDDEN
    mock_response.json.return_value = {
        "error_description": "Disallowed operation.",
    }
    mock_session.post.return_value = mock_response
    # Call the login method
    with pytest.raises(AuthenticationError) as excinfo:
        await kem.login("username", "password")
    assert str(excinfo.value) == "Authentication failed: Disallowed operation. Code 403"

    mock_session.post.side_effect = ClientConnectionError("Internet connection error")

    # Call the login method
    with pytest.raises(CommunicationError) as excinfo:
        await kem.login("username", "password")
    assert str(excinfo.value) == "Connection error: Internet connection error"


@pytest.mark.asyncio
async def test_get_homes():
    # Create a mock session
    mock_session = Mock()
    mock_session.get = AsyncMock()
    kem = AioKem(session=mock_session)
    kem._token = "test token"  # noqa: S105

    # Mock the response for the get_homes method
    mock_response = AsyncMock()
    mock_response.status = 200

    # Load the response data from the JSON file
    fixtures_path = Path(__file__).parent / "fixtures" / "homes.json"
    with fixtures_path.open() as f:
        mock_response_data = json.load(f)

    mock_response.json.return_value = mock_response_data
    mock_session.get.return_value = mock_response

    _ = await kem.get_homes()

    # Assert that the session.post method was called with the correct URL and data
    mock_session.get.assert_called_once()
    assert mock_session.get.call_args[0][0] == HOMES_URL
    assert mock_session.get.call_args[1]["headers"]["apikey"] == API_KEY
    assert (
        mock_session.get.call_args[1]["headers"]["authorization"]
        == f"bearer {kem._token}"
    )


@pytest.mark.asyncio
async def test_get_homes_exceptions():
    # Create a mock session
    mock_session = Mock()
    mock_session.get = AsyncMock()
    kem = AioKem(session=mock_session)

    # No token set
    with pytest.raises(AuthenticationError) as excinfo:
        await kem.get_homes()
    assert str(excinfo.value) == "Not authenticated"

    kem._token = "Test token"  # noqa: S105
    mock_response = AsyncMock()
    mock_response.status = HTTPStatus.UNAUTHORIZED
    mock_response.json.return_value = {
        "error_description": "Unauthorized.",
    }
    mock_session.get.return_value = mock_response

    # Call the login method
    with pytest.raises(AuthenticationError) as excinfo:
        await kem.get_homes()
    assert str(excinfo.value) == "Unauthorized: {response_data}"

    mock_response.status = HTTPStatus.BAD_REQUEST
    mock_response.json.return_value = "errordata"
    with pytest.raises(CommunicationError) as excinfo:
        await kem.get_homes()
    assert (
        str(excinfo.value)
        == f"Failed to fetch data: {HTTPStatus.BAD_REQUEST} errordata"
    )

    mock_session.get.side_effect = ClientConnectionError("Internet connection error")

    with pytest.raises(CommunicationError) as excinfo:
        await kem.get_homes()
    assert str(excinfo.value) == "Connection error: Internet connection error"


@pytest.mark.asyncio
async def test_get_generator_data():
    # Create a mock session
    mock_session = Mock()
    mock_session.get = AsyncMock()
    kem = AioKem(session=mock_session)
    kem._token = "test token"  # noqa: S105

    # Mock the response for the get_homes method
    mock_response = AsyncMock()
    mock_response.status = 200

    # Load the response data from the JSON file
    fixtures_path = Path(__file__).parent / "fixtures" / "generator_data.json"
    with fixtures_path.open() as f:
        mock_response_data = json.load(f)

    mock_response.json.return_value = mock_response_data
    mock_session.get.return_value = mock_response

    _ = await kem.get_generator_data(12345)

    # Assert that the session.post method was called with the correct URL and data
    mock_session.get.assert_called_once()
    assert (
        str(mock_session.get.call_args[0][0]) == f"{API_BASE}/kem/api/v3/devices/12345"
    )
    assert mock_session.get.call_args[1]["headers"]["apikey"] == API_KEY
    assert (
        mock_session.get.call_args[1]["headers"]["authorization"]
        == f"bearer {kem._token}"
    )
