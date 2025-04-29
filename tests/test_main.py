import logging
import time
from http import HTTPStatus
from unittest.mock import AsyncMock, Mock

import jwt
import pytest
from aiohttp import ClientConnectionError

from aiokem.exceptions import (
    AuthenticationCredentialsError,
    AuthenticationError,
    CommunicationError,
)
from aiokem.main import API_BASE, API_KEY, AUTHENTICATION_URL, HOMES_URL
from aiokem.message_logger import REDACTED
from tests.conftest import TestAioKem, get_kem, load_fixture_file


async def test_authenticate(caplog: pytest.LogCaptureFixture) -> None:
    """Tests the authenticate method."""
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = TestAioKem(session=mock_session)

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

    # Call the login method
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        await kem.authenticate("email", "password")

    # Assert that the access token and refresh token are set correctly
    assert kem._token == "mock_access_token"  # noqa: S105
    assert kem._refresh_token == "mock_refresh_token"  # noqa: S105
    # Assert that the session.post method was called with the correct URL and data
    mock_session.post.assert_called_once()
    assert mock_session.post.call_args[0][0] == AUTHENTICATION_URL
    assert mock_session.post.call_args[1]["data"] == {
        "grant_type": "password",
        "username": "email",
        "password": "password",
        "scope": "openid profile offline_access email",
    }

    assert '"access_token": "**redacted**"' in caplog.text
    assert '"refresh_token": "**redacted**"' in caplog.text


async def test_authenticate_with_refresh_token() -> None:
    """Tests the authenticate_with_refresh_token method."""
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = TestAioKem(session=mock_session)

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

    await kem.authenticate(
        email="email",
        password="password",  # noqa: S106
        refresh_token="mock_refresh_token",  # noqa: S106
    )

    # Assert that the access token and refresh token are set correctly
    assert kem._token == "mock_access_token"  # noqa: S105
    assert kem._refresh_token == "mock_refresh_token"  # noqa: S105
    # Assert that the session.post method was called with the correct URL and data
    mock_session.post.assert_called_once()
    assert mock_session.post.call_args[0][0] == AUTHENTICATION_URL
    assert mock_session.post.call_args[1]["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": kem._refresh_token,
        "scope": "openid profile offline_access email",
    }


async def test_refresh_token_callback() -> None:
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = TestAioKem(session=mock_session)

    # Mock the response for the login method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "token_type": "Bearer",
        "expires_in": 3600,
        "access_token": "mock_access_token",
        "refresh_token": "updated_refresh_token",
    }
    mock_session.post.return_value = mock_response

    await kem.authenticate_with_refresh_token("mock_refresh_token")

    assert kem.refreshed_token == "updated_refresh_token"  # noqa: S105
    assert kem.refreshed is True


async def test_authenticate_exceptions() -> None:
    # Create a mock session
    mock_session = Mock()
    mock_session.post = AsyncMock()
    kem = TestAioKem(session=mock_session)

    # Mock the response for the login method
    mock_response = AsyncMock()
    mock_response.status = HTTPStatus.BAD_REQUEST
    mock_response.json.return_value = {
        "error_description": "The credentials provided were invalid.",
    }
    mock_session.post.return_value = mock_response

    # Call the login method
    with pytest.raises(AuthenticationCredentialsError) as excinfo:
        await kem.authenticate("email", "password")

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
        await kem.authenticate("email", "password")
    assert str(excinfo.value) == "Authentication failed: Disallowed operation. Code 403"

    mock_session.post.side_effect = ClientConnectionError("Internet connection error")

    # Call the login method
    with pytest.raises(CommunicationError) as excinfo:
        await kem.authenticate("email", "password")
    assert str(excinfo.value) == "Connection error: Internet connection error"


async def test_get_homes(caplog: pytest.LogCaptureFixture) -> None:
    """Tests the get_homes method."""
    # Create a mock session
    mock_session = Mock()
    kem = await get_kem(mock_session)
    # Mock the response for the get_homes method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = load_fixture_file("homes.json")
    mock_session.get.return_value = mock_response

    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        _ = await kem.get_homes()

    # Assert that the session.post method was called with the correct URL and data
    mock_session.get.assert_called_once()
    assert mock_session.get.call_args[0][0] == HOMES_URL
    assert mock_session.get.call_args[1]["headers"]["apikey"] == API_KEY
    assert (
        mock_session.get.call_args[1]["headers"]["authorization"]
        == f"bearer {kem._token}"
    )

    assert "Generator 1" in caplog.text
    assert REDACTED in caplog.text


async def test_get_homes_exceptions() -> None:
    # Create a mock session
    mock_session = Mock()
    mock_session.get = AsyncMock()
    kem = TestAioKem(session=mock_session)

    # No token set
    with pytest.raises(AuthenticationError) as excinfo:
        await kem.get_homes()
    assert str(excinfo.value) == "Not authenticated"


async def test_get_generator_data() -> None:
    # Create a mock session
    mock_session = Mock()
    kem = await get_kem(mock_session)

    # Mock the response for the get_homes method
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_response.json.return_value = load_fixture_file("generator_data.json")
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


async def test_auto_refresh_token() -> None:
    """Tests the auto-refresh token functionality."""
    mock_session = Mock()
    kem = await get_kem(mock_session)
    mock_session.post.reset_mock()
    # Set the token to expire in the past
    token_expiration = kem._token_expires_at = time.monotonic() - 10000

    # Mock the response for the get_homes method
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = load_fixture_file("homes.json")
    mock_session.get.return_value = mock_response

    _ = await kem.get_homes()
    # Assert that the access token and refresh token are set correctly
    assert kem._token == "mock_access_token"  # noqa: S105
    assert kem._refresh_token == "mock_refresh_token"  # noqa: S105
    assert kem._token_expires_at > token_expiration
    mock_session.post.assert_called_once()
    assert mock_session.post.call_args[0][0] == AUTHENTICATION_URL
    assert mock_session.post.call_args[1]["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": kem._refresh_token,
        "scope": "openid profile offline_access email",
    }


async def test_close() -> None:
    """Tests the close method."""
    # Create a mock session
    mock_session = Mock()
    kem = await get_kem(mock_session)
    assert kem._session is not None

    await kem.close()

    assert kem._session is None


async def test_retries() -> None:
    mock_session = Mock()
    kem = await get_kem(mock_session)
    kem.set_retry_policy(0, [0, 0, 0])
    mock_session.get.side_effect = CommunicationError("Comms error")
    mock_session.get.reset_mock()
    with pytest.raises(CommunicationError):
        await kem.get_generator_data(12345)

    assert mock_session.get.call_count == 1

    kem.set_retry_policy(3, [0, 0, 0])

    mock_session.get.side_effect = CommunicationError("Comms error")
    mock_session.get.reset_mock()
    # Test a retryable error
    with pytest.raises(CommunicationError):
        await kem.get_generator_data(12345)
    assert mock_session.get.call_count == 4

    # Test a non-retryable error
    mock_session.get.side_effect = ValueError("An exception")
    mock_session.get.reset_mock()

    with pytest.raises(ValueError):
        await kem.get_generator_data(12345)

    assert mock_session.get.call_count == 1

    # Test an authentication error
    # This should result in reauthenticating.
    mock_response = AsyncMock()
    mock_response.status = 200
    generator = load_fixture_file("generator_data.json")
    mock_response.json.return_value = generator
    mock_session.get.reset_mock()
    mock_session.get.side_effect = [
        AuthenticationError("An exception"),
        mock_response,
    ]
    mock_session.post.reset_mock()

    response = await kem.get_generator_data(12345)

    assert response == generator
    assert mock_session.get.call_count == 2
    assert mock_session.post.call_count == 1

    # Test a persistent authentication error
    # This should result in failure with no retries.
    mock_session.post.reset_mock()
    mock_session.post.side_effect = AuthenticationError("Unauthorized")
    mock_session.get.reset_mock()
    mock_session.get.side_effect = [
        AuthenticationError("An exception"),
        generator,
    ]

    with pytest.raises(AuthenticationError):
        await kem.get_generator_data(12345)

    assert mock_session.post.call_count == 1
    assert mock_session.get.call_count == 1


async def test_get_subject() -> None:
    mock_session = Mock()
    kem = await get_kem(mock_session)
    # The mock token is not a JWT, so the subject should be None
    subject = kem.get_token_subject()
    assert subject is None

    subject_email = "myemail@email.com"
    # Create a fake token with a subject.
    payload = {
        "sub": subject_email,
        "name": "John Doe",
        "iat": int(time.time()),  # Issued at
        "exp": int(time.time()) + 3600,  # Expiration time (1 hour from now)
    }
    secret_key = "your-secret-key"  # noqa: S105
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    kem._token = token
    assert kem.get_token_subject() == subject_email
