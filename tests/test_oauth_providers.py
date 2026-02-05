"""
Unit tests for OAuth provider implementations.

Tests Google, Facebook, and Twitter OAuth provider classes including
authorization URL generation, token exchange, user info retrieval, and token refresh.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.user_management.services.oauth.base import (
    BaseOAuthProvider,
    OAuthTokenResponse,
    OAuthUserInfo,
)
from src.user_management.services.oauth.facebook import FacebookOAuthProvider
from src.user_management.services.oauth.google import GoogleOAuthProvider
from src.user_management.services.oauth.twitter import TwitterOAuthProvider


@pytest.fixture
def google_provider():
    """Create Google OAuth provider instance."""
    return GoogleOAuthProvider(
        client_id="test_google_client_id",
        client_secret="test_google_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )


@pytest.fixture
def facebook_provider():
    """Create Facebook OAuth provider instance."""
    return FacebookOAuthProvider(
        client_id="test_facebook_client_id",
        client_secret="test_facebook_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )


@pytest.fixture
def twitter_provider():
    """Create Twitter OAuth provider instance."""
    return TwitterOAuthProvider(
        client_id="test_twitter_client_id",
        client_secret="test_twitter_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )


@pytest.fixture
def mock_http_client():
    """Create mock HTTP client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


# Google OAuth Provider Tests


@pytest.mark.unit
def test_google_provider_initialization(google_provider):
    """Test Google provider initialization."""
    assert google_provider.provider_name == "google"
    assert google_provider.client_id == "test_google_client_id"
    assert google_provider.client_secret == "test_google_client_secret"
    assert google_provider.redirect_uri == "http://localhost:8000/callback"


@pytest.mark.unit
def test_google_provider_properties(google_provider):
    """Test Google provider properties."""
    assert google_provider.authorization_url == "https://accounts.google.com/o/oauth2/v2/auth"
    assert google_provider.token_url == "https://oauth2.googleapis.com/token"
    assert google_provider.user_info_url == "https://www.googleapis.com/oauth2/v2/userinfo"
    assert "openid" in google_provider.default_scopes
    assert "https://www.googleapis.com/auth/userinfo.email" in google_provider.default_scopes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_generate_auth_url(google_provider):
    """Test Google authorization URL generation."""
    auth_url, state = await google_provider.generate_auth_url(state="test_state_123")
    
    assert "accounts.google.com" in auth_url
    assert "client_id=test_google_client_id" in auth_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in auth_url
    assert "response_type=code" in auth_url
    assert "state=test_state_123" in auth_url
    assert state == "test_state_123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_generate_auth_url_with_custom_scopes(google_provider):
    """Test Google authorization URL with custom scopes."""
    custom_scopes = ["openid", "email"]
    auth_url, state = await google_provider.generate_auth_url(scopes=custom_scopes)
    
    assert "scope=openid+email" in auth_url or "scope=openid%20email" in auth_url
    assert len(state) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_handle_callback_success(google_provider, mock_http_client):
    """Test successful Google OAuth callback."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "google_access_token_123",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "google_refresh_token_456",
        "scope": "openid email profile",
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    token_response = await google_provider.handle_callback(code="test_auth_code")
    
    assert token_response.access_token == "google_access_token_123"
    assert token_response.token_type == "Bearer"
    assert token_response.expires_in == 3600
    assert token_response.refresh_token == "google_refresh_token_456"
    
    mock_http_client.post.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_get_user_info_success(google_provider, mock_http_client):
    """Test successful Google user info retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "google_user_123",
        "email": "test@gmail.com",
        "name": "Test User",
        "picture": "https://lh3.googleusercontent.com/a/default",
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    user_info = await google_provider.get_user_info(access_token="test_token")
    
    assert user_info.provider_user_id == "google_user_123"
    assert user_info.email == "test@gmail.com"
    assert user_info.name == "Test User"
    assert user_info.avatar_url == "https://lh3.googleusercontent.com/a/default"
    
    mock_http_client.get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_parse_user_info(google_provider):
    """Test Google user info parsing."""
    raw_data = {
        "id": "123456",
        "email": "user@gmail.com",
        "name": "John Doe",
        "picture": "https://example.com/photo.jpg",
    }
    
    user_info = await google_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "123456"
    assert user_info.email == "user@gmail.com"
    assert user_info.name == "John Doe"
    assert user_info.avatar_url == "https://example.com/photo.jpg"
    assert user_info.profile_url is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_refresh_token(google_provider, mock_http_client):
    """Test Google token refresh."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token_789",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    token_response = await google_provider.refresh_token(refresh_token="old_refresh_token")
    
    assert token_response.access_token == "new_access_token_789"
    assert token_response.expires_in == 3600


# Facebook OAuth Provider Tests


@pytest.mark.unit
def test_facebook_provider_initialization(facebook_provider):
    """Test Facebook provider initialization."""
    assert facebook_provider.provider_name == "facebook"
    assert facebook_provider.client_id == "test_facebook_client_id"
    assert facebook_provider.client_secret == "test_facebook_client_secret"


@pytest.mark.unit
def test_facebook_provider_properties(facebook_provider):
    """Test Facebook provider properties."""
    assert "www.facebook.com" in facebook_provider.authorization_url
    assert "graph.facebook.com" in facebook_provider.token_url
    assert "graph.facebook.com" in facebook_provider.user_info_url
    assert "email" in facebook_provider.default_scopes
    assert "public_profile" in facebook_provider.default_scopes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_generate_auth_url(facebook_provider):
    """Test Facebook authorization URL generation."""
    auth_url, state = await facebook_provider.generate_auth_url(state="fb_state_456")
    
    assert "www.facebook.com" in auth_url
    assert "client_id=test_facebook_client_id" in auth_url
    assert "state=fb_state_456" in auth_url
    assert state == "fb_state_456"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_handle_callback_success(facebook_provider, mock_http_client):
    """Test successful Facebook OAuth callback."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "facebook_token_abc",
        "token_type": "Bearer",
        "expires_in": 5400,
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    facebook_provider._http_client = mock_http_client
    
    token_response = await facebook_provider.handle_callback(code="fb_auth_code")
    
    assert token_response.access_token == "facebook_token_abc"
    assert token_response.token_type == "Bearer"
    assert token_response.expires_in == 5400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_get_user_info_success(facebook_provider, mock_http_client):
    """Test successful Facebook user info retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "fb_user_789",
        "name": "Facebook User",
        "email": "fbuser@example.com",
        "picture": {
            "data": {
                "url": "https://graph.facebook.com/789/picture"
            }
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response
    
    facebook_provider._http_client = mock_http_client
    
    user_info = await facebook_provider.get_user_info(access_token="fb_token")
    
    assert user_info.provider_user_id == "fb_user_789"
    assert user_info.email == "fbuser@example.com"
    assert user_info.name == "Facebook User"
    assert "graph.facebook.com" in user_info.avatar_url
    assert "facebook.com/fb_user_789" in user_info.profile_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_parse_user_info(facebook_provider):
    """Test Facebook user info parsing."""
    raw_data = {
        "id": "987654",
        "name": "Jane Smith",
        "email": "jane@facebook.com",
        "picture": {
            "data": {
                "url": "https://example.com/picture.jpg"
            }
        },
    }
    
    user_info = await facebook_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "987654"
    assert user_info.email == "jane@facebook.com"
    assert user_info.name == "Jane Smith"
    assert user_info.avatar_url == "https://example.com/picture.jpg"
    assert "facebook.com/987654" in user_info.profile_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_parse_user_info_without_picture(facebook_provider):
    """Test Facebook user info parsing when picture is missing."""
    raw_data = {
        "id": "111222",
        "name": "No Picture User",
        "email": "nopicture@facebook.com",
    }
    
    user_info = await facebook_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "111222"
    assert user_info.avatar_url is None


# Twitter OAuth Provider Tests


@pytest.mark.unit
def test_twitter_provider_initialization(twitter_provider):
    """Test Twitter provider initialization."""
    assert twitter_provider.provider_name == "twitter"
    assert twitter_provider.client_id == "test_twitter_client_id"
    assert twitter_provider.client_secret == "test_twitter_client_secret"


@pytest.mark.unit
def test_twitter_provider_properties(twitter_provider):
    """Test Twitter provider properties."""
    assert "twitter.com" in twitter_provider.authorization_url
    assert "api.twitter.com" in twitter_provider.token_url
    assert "api.twitter.com" in twitter_provider.user_info_url
    assert "tweet.read" in twitter_provider.default_scopes
    assert "users.read" in twitter_provider.default_scopes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_generate_auth_url(twitter_provider):
    """Test Twitter authorization URL generation with PKCE."""
    auth_url, state = await twitter_provider.generate_auth_url(state="twitter_state_789")
    
    assert "twitter.com" in auth_url
    assert "client_id=test_twitter_client_id" in auth_url
    assert "state=twitter_state_789" in auth_url
    assert "code_challenge" in auth_url
    assert "code_challenge_method=plain" in auth_url
    assert state == "twitter_state_789"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_handle_callback_success(twitter_provider, mock_http_client):
    """Test successful Twitter OAuth callback."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "twitter_token_xyz",
        "token_type": "Bearer",
        "expires_in": 7200,
        "refresh_token": "twitter_refresh_123",
        "scope": "tweet.read users.read",
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    twitter_provider._http_client = mock_http_client
    
    token_response = await twitter_provider.handle_callback(code="twitter_code")
    
    assert token_response.access_token == "twitter_token_xyz"
    assert token_response.token_type == "Bearer"
    assert token_response.expires_in == 7200
    assert token_response.refresh_token == "twitter_refresh_123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_get_user_info_success(twitter_provider, mock_http_client):
    """Test successful Twitter user info retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "id": "twitter_user_456",
            "name": "Twitter User",
            "username": "twitteruser",
            "profile_image_url": "https://pbs.twimg.com/profile_images/456/photo.jpg",
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get.return_value = mock_response
    
    twitter_provider._http_client = mock_http_client
    
    user_info = await twitter_provider.get_user_info(access_token="twitter_token")
    
    assert user_info.provider_user_id == "twitter_user_456"
    assert user_info.name == "Twitter User"
    assert user_info.email is None  # Twitter doesn't always provide email
    assert "pbs.twimg.com" in user_info.avatar_url
    assert "twitter.com/twitteruser" in user_info.profile_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_parse_user_info(twitter_provider):
    """Test Twitter user info parsing."""
    raw_data = {
        "data": {
            "id": "123789",
            "name": "John Twitter",
            "username": "johntwitter",
            "profile_image_url": "https://example.com/profile.jpg",
        }
    }
    
    user_info = await twitter_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "123789"
    assert user_info.name == "John Twitter"
    assert user_info.email is None
    assert user_info.avatar_url == "https://example.com/profile.jpg"
    assert "twitter.com/johntwitter" in user_info.profile_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_parse_user_info_without_username(twitter_provider):
    """Test Twitter user info parsing when username is missing."""
    raw_data = {
        "data": {
            "id": "999888",
            "name": "No Username",
        }
    }
    
    user_info = await twitter_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "999888"
    assert user_info.profile_url is None


# Base Provider Tests


@pytest.mark.unit
def test_base_provider_state_generation(google_provider):
    """Test state parameter generation."""
    state1 = google_provider.generate_state()
    state2 = google_provider.generate_state()
    
    assert len(state1) > 20
    assert len(state2) > 20
    assert state1 != state2


@pytest.mark.unit
def test_base_provider_state_validation(google_provider):
    """Test state parameter validation."""
    state = "test_state_12345"
    
    # Valid state
    assert google_provider.validate_state(state, state) is True
    
    # Invalid state
    assert google_provider.validate_state(state, "different_state") is False
    assert google_provider.validate_state("", state) is False
    assert google_provider.validate_state(state, "") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_http_client_creation(google_provider):
    """Test HTTP client lazy creation."""
    assert google_provider._http_client is None
    
    client = google_provider.http_client
    assert client is not None
    assert isinstance(client, httpx.AsyncClient)
    
    # Should return same client
    client2 = google_provider.http_client
    assert client is client2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_close(google_provider):
    """Test provider HTTP client cleanup."""
    # Create client
    client = google_provider.http_client
    assert client is not None
    
    # Close provider
    await google_provider.close()
    
    # Client should be closed (we can't directly verify, but no error should occur)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_callback_with_http_error(google_provider, mock_http_client):
    """Test callback handling with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request",
        request=MagicMock(),
        response=MagicMock(status_code=400),
    )
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    with pytest.raises(httpx.HTTPStatusError):
        await google_provider.handle_callback(code="invalid_code")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_info_with_http_error(google_provider, mock_http_client):
    """Test user info retrieval with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    mock_http_client.get.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    with pytest.raises(httpx.HTTPStatusError):
        await google_provider.get_user_info(access_token="invalid_token")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_token_with_http_error(google_provider, mock_http_client):
    """Test token refresh with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Invalid Grant",
        request=MagicMock(),
        response=MagicMock(status_code=400),
    )
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    with pytest.raises(httpx.HTTPStatusError):
        await google_provider.refresh_token(refresh_token="expired_refresh_token")


# Integration-like Tests for Provider Coordination


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_providers_initialization():
    """Test initializing multiple providers."""
    google = GoogleOAuthProvider(
        client_id="google_id",
        client_secret="google_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    
    facebook = FacebookOAuthProvider(
        client_id="facebook_id",
        client_secret="facebook_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    
    twitter = TwitterOAuthProvider(
        client_id="twitter_id",
        client_secret="twitter_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    
    assert google.provider_name == "google"
    assert facebook.provider_name == "facebook"
    assert twitter.provider_name == "twitter"
    
    await google.close()
    await facebook.close()
    await twitter.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_with_custom_http_client():
    """Test provider with custom HTTP client."""
    custom_client = httpx.AsyncClient(timeout=60.0)
    
    provider = GoogleOAuthProvider(
        client_id="test_id",
        client_secret="test_secret",
        redirect_uri="http://localhost:8000/callback",
        http_client=custom_client,
    )
    
    assert provider._http_client is custom_client
    assert provider.http_client is custom_client
    
    await provider.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_google_auth_url_contains_required_scopes(google_provider):
    """Test that Google auth URL includes required scopes."""
    auth_url, _ = await google_provider.generate_auth_url()
    
    # Check for openid scope (required for Google)
    assert "openid" in auth_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_facebook_user_info_with_nested_picture(facebook_provider):
    """Test Facebook user info parsing with nested picture structure."""
    raw_data = {
        "id": "12345",
        "name": "Test User",
        "email": "test@example.com",
        "picture": {
            "data": {
                "height": 50,
                "width": 50,
                "url": "https://platform-lookaside.fbsbx.com/platform/profilepic/",
            }
        },
    }
    
    user_info = await facebook_provider._parse_user_info(raw_data)
    
    assert user_info.avatar_url == "https://platform-lookaside.fbsbx.com/platform/profilepic/"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twitter_auth_url_includes_pkce_challenge(twitter_provider):
    """Test that Twitter auth URL includes PKCE challenge parameters."""
    auth_url, state = await twitter_provider.generate_auth_url()
    
    assert "code_challenge=" in auth_url
    assert "code_challenge_method=" in auth_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_token_response_with_minimal_data(google_provider, mock_http_client):
    """Test handling token response with minimal required fields."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "minimal_token",
        # Only access_token is strictly required
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    token_response = await google_provider.handle_callback(code="test_code")
    
    assert token_response.access_token == "minimal_token"
    assert token_response.token_type == "Bearer"  # Default value
    assert token_response.expires_in is None
    assert token_response.refresh_token is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_info_with_missing_optional_fields(google_provider):
    """Test user info parsing with missing optional fields."""
    raw_data = {
        "id": "123",
        # email, name, picture are all optional
    }
    
    user_info = await google_provider._parse_user_info(raw_data)
    
    assert user_info.provider_user_id == "123"
    assert user_info.email is None
    assert user_info.name is None
    assert user_info.avatar_url is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_token_preserves_old_refresh_token(google_provider, mock_http_client):
    """Test that refresh preserves old refresh token if new one not provided."""
    old_refresh_token = "old_refresh_token_123"
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        # No refresh_token in response
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post.return_value = mock_response
    
    google_provider._http_client = mock_http_client
    
    token_response = await google_provider.refresh_token(refresh_token=old_refresh_token)
    
    assert token_response.access_token == "new_access_token"
    assert token_response.refresh_token == old_refresh_token  # Old token preserved


@pytest.mark.unit
def test_oauth_user_info_model():
    """Test OAuthUserInfo model creation and validation."""
    user_info = OAuthUserInfo(
        provider_user_id="test_123",
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        profile_url="https://example.com/profile",
        raw_data={"custom": "data"},
    )
    
    assert user_info.provider_user_id == "test_123"
    assert user_info.email == "test@example.com"
    assert user_info.name == "Test User"
    assert user_info.avatar_url == "https://example.com/avatar.jpg"
    assert user_info.profile_url == "https://example.com/profile"
    assert user_info.raw_data == {"custom": "data"}


@pytest.mark.unit
def test_oauth_token_response_model():
    """Test OAuthTokenResponse model creation and validation."""
    token_response = OAuthTokenResponse(
        access_token="access_123",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="refresh_456",
        scope="email profile",
        raw_data={"extra": "field"},
    )
    
    assert token_response.access_token == "access_123"
    assert token_response.token_type == "Bearer"
    assert token_response.expires_in == 3600
    assert token_response.refresh_token == "refresh_456"
    assert token_response.scope == "email profile"
    assert token_response.raw_data == {"extra": "field"}
