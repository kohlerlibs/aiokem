import pytest
from aiokem.main import AUTHENTICATION_URL, AioKem
from unittest.mock import AsyncMock, Mock

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
        'access_token': 'mock_access_token',
        'refresh_token': 'mock_refresh_token'
    }
    mock_session.post.return_value = mock_response

    # Call the login method
    await kem.login('username', 'password')

    # Assert that the access token and refresh token are set correctly
    assert kem._token == 'mock_access_token'
    assert kem._refresh_token == 'mock_refresh_token'
    # Assert that the session.post method was called with the correct URL and data
    mock_session.post.assert_called_once()
    assert mock_session.post.call_args[0][0] == AUTHENTICATION_URL
    assert mock_session.post.call_args[1]['data'] == {
        'grant_type': 'password',
        'username': 'username',
        'password': 'password',
        'scope': 'openid profile offline_access email'
    }
    

