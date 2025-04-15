from http import HTTPStatus
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientConnectionError

from aiokem.exceptions import (
    AuthenticationCredentialsError,
    AuthenticationError,
    CommunicationError,
)
from aiokem.main import AUTHENTICATION_URL, AioKem


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
