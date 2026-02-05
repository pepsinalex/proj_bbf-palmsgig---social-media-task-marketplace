"""
Integration tests for OAuth 2.0 authentication flow.

Tests OAuth authentication endpoints including authorization URL generation,
callback handling, account linking/unlinking, and social account management.
"""

import os
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.main import app
from src.shared.models.auth import AuthenticationMethod, OAuthToken
from src.shared.models.user import User
from src.user_management.services.oauth.base import OAuthTokenResponse, OAuthUserInfo


@pytest.fixture
def mock_oauth_env_vars(monkeypatch):
    """Set up OAuth environment variables for testing."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_google_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_google_client_secret")
    monkeypatch.setenv("FACEBOOK_CLIENT_ID", "test_facebook_client_id")
    monkeypatch.setenv("FACEBOOK_CLIENT_SECRET", "test_facebook_client_secret")
    monkeypatch.setenv("TWITTER_CLIENT_ID", "test_twitter_client_id")
    monkeypatch.setenv("TWITTER_CLIENT_SECRET", "test_twitter_client_secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback")


@pytest.fixture
def mock_oauth_token_response() -> OAuthTokenResponse:
    """Mock OAuth token response."""
    return OAuthTokenResponse(
        access_token="mock_access_token_12345",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="mock_refresh_token_67890",
        scope="email profile",
        raw_data={},
    )


@pytest.fixture
def mock_google_user_info() -> OAuthUserInfo:
    """Mock Google user info."""
    return OAuthUserInfo(
        provider_user_id="google_123456789",
        email="testuser@gmail.com",
        name="Test User",
        avatar_url="https://lh3.googleusercontent.com/a/default-user",
        profile_url=None,
        raw_data={
            "id": "google_123456789",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/a/default-user",
        },
    )


@pytest.fixture
def mock_facebook_user_info() -> OAuthUserInfo:
    """Mock Facebook user info."""
    return OAuthUserInfo(
        provider_user_id="facebook_987654321",
        email="testuser@facebook.com",
        name="Test Facebook User",
        avatar_url="https://graph.facebook.com/987654321/picture",
        profile_url="https://www.facebook.com/987654321",
        raw_data={
            "id": "facebook_987654321",
            "email": "testuser@facebook.com",
            "name": "Test Facebook User",
        },
    )


@pytest.fixture
def mock_twitter_user_info() -> OAuthUserInfo:
    """Mock Twitter user info."""
    return OAuthUserInfo(
        provider_user_id="twitter_456789123",
        email=None,
        name="Test Twitter User",
        avatar_url="https://pbs.twimg.com/profile_images/123/test.jpg",
        profile_url="https://twitter.com/testuser",
        raw_data={
            "data": {
                "id": "twitter_456789123",
                "name": "Test Twitter User",
                "username": "testuser",
                "profile_image_url": "https://pbs.twimg.com/profile_images/123/test.jpg",
            }
        },
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_oauth_providers(mock_oauth_env_vars):
    """Test listing available OAuth providers."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total" in data
        assert data["total"] == 3
        
        provider_names = [p["provider"] for p in data["providers"]]
        assert "google" in provider_names
        assert "facebook" in provider_names
        assert "twitter" in provider_names
        
        # Check that all providers are configured
        for provider in data["providers"]:
            assert provider["is_configured"] is True
            assert provider["is_available"] is True
            assert "display_name" in provider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_oauth_providers_without_config():
    """Test listing OAuth providers when none are configured."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # All providers should exist but not be configured
        for provider in data["providers"]:
            assert provider["is_configured"] is False
            assert provider["is_available"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_google_authorization_url(mock_oauth_env_vars):
    """Test generating Google OAuth authorization URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/oauth/authorize/google",
            params={"state": "test_state_12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["provider"] == "google"
        assert data["state"] == "test_state_12345"
        assert "accounts.google.com" in data["authorization_url"]
        assert "client_id=test_google_client_id" in data["authorization_url"]
        assert "state=test_state_12345" in data["authorization_url"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_facebook_authorization_url(mock_oauth_env_vars):
    """Test generating Facebook OAuth authorization URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/authorize/facebook")
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["provider"] == "facebook"
        assert "www.facebook.com" in data["authorization_url"]
        assert "client_id=test_facebook_client_id" in data["authorization_url"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_twitter_authorization_url(mock_oauth_env_vars):
    """Test generating Twitter OAuth authorization URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/authorize/twitter")
        
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["provider"] == "twitter"
        assert "twitter.com" in data["authorization_url"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_authorization_url_invalid_provider(mock_oauth_env_vars):
    """Test generating authorization URL with invalid provider."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/authorize/invalid_provider")
        
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_authorization_url_unconfigured_provider():
    """Test generating authorization URL when provider is not configured."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/authorize/google")
        
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_new_user_google(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
):
    """Test OAuth callback for new user with Google."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            response = await client.get(
                "/api/v1/oauth/callback",
                params={
                    "provider": "google",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["is_new_user"] is True
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == "testuser@gmail.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_existing_user(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
):
    """Test OAuth callback for existing user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First, create the user via OAuth
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            first_response = await client.get(
                "/api/v1/oauth/callback",
                params={
                    "provider": "google",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
            )
            assert first_response.status_code == 200
            
            # Second login with same OAuth account
            second_response = await client.get(
                "/api/v1/oauth/callback",
                params={
                    "provider": "google",
                    "code": "test_auth_code_67890",
                    "state": "test_state_67890",
                },
            )
            
            assert second_response.status_code == 200
            data = second_response.json()
            assert data["success"] is True
            assert data["is_new_user"] is False
            assert "access_token" in data
            assert data["user"]["email"] == "testuser@gmail.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_missing_code(mock_oauth_env_vars):
    """Test OAuth callback with missing authorization code."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/oauth/callback",
            params={
                "provider": "google",
                "state": "test_state_12345",
            },
        )
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_invalid_provider(mock_oauth_env_vars):
    """Test OAuth callback with invalid provider."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/oauth/callback",
            params={
                "provider": "invalid_provider",
                "code": "test_auth_code_12345",
                "state": "test_state_12345",
            },
        )
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_token_exchange_failure(mock_oauth_env_vars):
    """Test OAuth callback when token exchange fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            side_effect=Exception("Token exchange failed"),
        ):
            response = await client.get(
                "/api/v1/oauth/callback",
                params={
                    "provider": "google",
                    "code": "invalid_code",
                    "state": "test_state_12345",
                },
            )
            
            assert response.status_code == 500


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_social_account(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_facebook_user_info,
):
    """Test linking a social account to existing user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First, register a regular user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "regular_user@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567890",
                "username": "regularuser",
            },
        )
        assert register_response.status_code == 201
        
        # Login to get access token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "regular_user@example.com",
                "password": "SecureP@ss123",
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Link Facebook account
        with patch(
            "src.user_management.services.oauth.facebook.FacebookOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.facebook.FacebookOAuthProvider.get_user_info",
            return_value=mock_facebook_user_info,
        ):
            link_response = await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "facebook",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            assert link_response.status_code == 200
            data = link_response.json()
            assert data["success"] is True
            assert "social_account" in data
            assert data["social_account"]["provider"] == "facebook"
            assert data["social_account"]["email"] == "testuser@facebook.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_social_account_already_linked(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
):
    """Test linking a social account that is already linked to another user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create first user via OAuth
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            await client.get(
                "/api/v1/oauth/callback",
                params={
                    "provider": "google",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
            )
        
        # Register second user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "second_user@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567891",
                "username": "seconduser",
            },
        )
        assert register_response.status_code == 201
        
        # Login as second user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "second_user@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Try to link the same Google account
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            link_response = await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "google",
                    "code": "test_auth_code_67890",
                    "state": "test_state_67890",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            assert link_response.status_code == 400
            assert "already linked" in link_response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_social_account_unauthenticated():
    """Test linking social account without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/link",
            json={
                "provider": "google",
                "code": "test_auth_code_12345",
                "state": "test_state_12345",
            },
        )
        
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unlink_social_account(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
):
    """Test unlinking a social account."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user with password
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_with_password@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567892",
                "username": "userpass",
            },
        )
        assert register_response.status_code == 201
        
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user_with_password@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Link Google account
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "google",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        
        # Unlink Google account
        unlink_response = await client.post(
            "/api/v1/oauth/unlink",
            json={"provider": "google"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert unlink_response.status_code == 200
        data = unlink_response.json()
        assert data["success"] is True
        assert data["provider"] == "google"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unlink_nonexistent_social_account(mock_oauth_env_vars):
    """Test unlinking a social account that is not linked."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_no_social@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567893",
                "username": "nosocial",
            },
        )
        assert register_response.status_code == 201
        
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user_no_social@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Try to unlink non-existent account
        unlink_response = await client.post(
            "/api/v1/oauth/unlink",
            json={"provider": "google"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert unlink_response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unlink_social_account_unauthenticated():
    """Test unlinking social account without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/unlink",
            json={"provider": "google"},
        )
        
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_linked_accounts(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
):
    """Test listing user's linked social accounts."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_list_accounts@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567894",
                "username": "listaccounts",
            },
        )
        assert register_response.status_code == 201
        
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user_list_accounts@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Link Google account
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "google",
                    "code": "test_auth_code_12345",
                    "state": "test_state_12345",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        
        # List linked accounts
        list_response = await client.get(
            "/api/v1/oauth/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        assert "accounts" in data
        assert data["total"] == 1
        assert data["accounts"][0]["provider"] == "google"
        assert data["accounts"][0]["email"] == "testuser@gmail.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_linked_accounts_empty(mock_oauth_env_vars):
    """Test listing linked accounts when none exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user_no_links@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567895",
                "username": "nolinks",
            },
        )
        assert register_response.status_code == 201
        
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user_no_links@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # List linked accounts
        list_response = await client.get(
            "/api/v1/oauth/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["accounts"] == []
        assert data["total"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_linked_accounts_unauthenticated():
    """Test listing linked accounts without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/accounts")
        
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_multiple_providers(
    mock_oauth_env_vars,
    mock_oauth_token_response,
    mock_google_user_info,
    mock_facebook_user_info,
):
    """Test OAuth callback with multiple providers for the same user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user with password
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "multi_provider@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567896",
                "username": "multiprovider",
            },
        )
        assert register_response.status_code == 201
        
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "multi_provider@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Link Google account
        with patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.google.GoogleOAuthProvider.get_user_info",
            return_value=mock_google_user_info,
        ):
            google_link = await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "google",
                    "code": "google_code",
                    "state": "google_state",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert google_link.status_code == 200
        
        # Link Facebook account
        with patch(
            "src.user_management.services.oauth.facebook.FacebookOAuthProvider.handle_callback",
            return_value=mock_oauth_token_response,
        ), patch(
            "src.user_management.services.oauth.facebook.FacebookOAuthProvider.get_user_info",
            return_value=mock_facebook_user_info,
        ):
            facebook_link = await client.post(
                "/api/v1/oauth/link",
                json={
                    "provider": "facebook",
                    "code": "facebook_code",
                    "state": "facebook_state",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert facebook_link.status_code == 200
        
        # List all linked accounts
        list_response = await client.get(
            "/api/v1/oauth/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] == 2
        providers = [acc["provider"] for acc in data["accounts"]]
        assert "google" in providers
        assert "facebook" in providers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_oauth_callback_error_handling(mock_oauth_env_vars):
    """Test error handling in OAuth callback."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with error parameter from OAuth provider
        response = await client.get(
            "/api/v1/oauth/callback",
            params={
                "provider": "google",
                "error": "access_denied",
                "error_description": "User denied access",
            },
        )
        
        # Should handle the error gracefully
        assert response.status_code in [400, 422]
