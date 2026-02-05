"""
Tests for Social Accounts API Router.

Integration tests for social accounts API endpoints including OAuth flows,
account linking, verification, error handling, authentication, and
complete integration workflows using FastAPI TestClient.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.social_media.enums.platform_enums import Platform
from src.social_media.models.social_account import SocialAccount
from src.social_media.routers.social_accounts import router
from src.social_media.schemas.social_account import AccountInfo

logger = logging.getLogger(__name__)


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI application for testing."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def authenticated_user_id() -> str:
    """Return authenticated user ID for tests."""
    return "user-123"


@pytest.fixture
def sample_account() -> SocialAccount:
    """Create sample social account."""
    account = SocialAccount(
        id="account-123",
        user_id="user-123",
        platform=Platform.FACEBOOK.value,
        account_id="fb_account_123",
        username="johndoe",
        display_name="John Doe",
        access_token=SocialAccount.encrypt_token("test_access_token"),
        refresh_token=SocialAccount.encrypt_token("test_refresh_token"),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        scope="email profile",
        is_verified=True,
        last_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return account


class TestConnectAccountEndpoint:
    """Tests for account connection initiation endpoint."""

    def test_connect_account_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test successful connection initiation."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class:
            mock_oauth = AsyncMock()
            mock_oauth.generate_authorization_url = AsyncMock(
                return_value={
                    "authorization_url": "https://facebook.com/oauth?...",
                    "state": "test_state_token",
                }
            )
            mock_oauth_class.return_value = mock_oauth

            response = client.get("/social-accounts/connect/facebook")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert "platform" in data
            assert data["platform"] == "facebook"

    def test_connect_account_invalid_platform(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test connection with invalid platform."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch("src.social_media.routers.social_accounts.get_database_session"):
            response = client.get("/social-accounts/connect/invalid_platform")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_connect_account_with_custom_scopes(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test connection with custom OAuth scopes."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class:
            mock_oauth = AsyncMock()
            mock_oauth.generate_authorization_url = AsyncMock(
                return_value={
                    "authorization_url": "https://facebook.com/oauth?...",
                    "state": "test_state_token",
                }
            )
            mock_oauth_class.return_value = mock_oauth

            response = client.get(
                "/social-accounts/connect/facebook",
                params={"scopes": ["email", "public_profile"]},
            )

            assert response.status_code == status.HTTP_200_OK

    def test_connect_account_requires_authentication(self, client: TestClient) -> None:
        """Test connection requires authentication."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            side_effect=Exception("Unauthorized"),
        ):
            with pytest.raises(Exception, match="Unauthorized"):
                client.get("/social-accounts/connect/facebook")

    def test_connect_account_oauth_service_error(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test connection handles OAuth service errors."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class:
            mock_oauth = AsyncMock()
            mock_oauth.generate_authorization_url = AsyncMock(
                side_effect=ValueError("OAuth error")
            )
            mock_oauth_class.return_value = mock_oauth

            response = client.get("/social-accounts/connect/facebook")

            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestOAuthCallbackEndpoint:
    """Tests for OAuth callback endpoint."""

    def test_oauth_callback_success(
        self,
        client: TestClient,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful OAuth callback."""
        with patch(
            "src.social_media.routers.social_accounts.get_database_session",
            return_value=mock_session,
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class, patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_account_class:
            # Mock OAuth service
            mock_oauth = AsyncMock()
            mock_oauth.handle_callback = AsyncMock(
                return_value={
                    "access_token": "test_token",
                    "refresh_token": "test_refresh",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "scope": "email profile",
                }
            )
            mock_oauth_class.return_value = mock_oauth

            # Mock Account service
            mock_account_service = AsyncMock()
            mock_account_service.link_account = AsyncMock(return_value=sample_account)
            mock_account_class.return_value = mock_account_service

            response = client.get(
                "/social-accounts/callback/facebook",
                params={
                    "code": "auth_code_123",
                    "state": "test_state",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["platform"] == Platform.FACEBOOK.value
            assert data["username"] == "johndoe"

    def test_oauth_callback_with_error(self, client: TestClient) -> None:
        """Test callback with OAuth error."""
        with patch("src.social_media.routers.social_accounts.get_database_session"):
            response = client.get(
                "/social-accounts/callback/facebook",
                params={
                    "error": "access_denied",
                    "error_description": "User denied access",
                    "state": "test_state",
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "access_denied" in response.json()["detail"]

    def test_oauth_callback_missing_code(self, client: TestClient) -> None:
        """Test callback with missing authorization code."""
        with patch("src.social_media.routers.social_accounts.get_database_session"):
            response = client.get(
                "/social-accounts/callback/facebook",
                params={"state": "test_state"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_oauth_callback_missing_state(self, client: TestClient) -> None:
        """Test callback with missing state parameter."""
        with patch("src.social_media.routers.social_accounts.get_database_session"):
            response = client.get(
                "/social-accounts/callback/facebook",
                params={"code": "auth_code_123"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_oauth_callback_state_validation_failure(
        self,
        client: TestClient,
        mock_session: AsyncMock,
    ) -> None:
        """Test callback with state validation failure."""
        with patch(
            "src.social_media.routers.social_accounts.get_database_session",
            return_value=mock_session,
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class:
            mock_oauth = AsyncMock()
            mock_oauth.handle_callback = AsyncMock(
                side_effect=ValueError("State validation failed")
            )
            mock_oauth_class.return_value = mock_oauth

            response = client.get(
                "/social-accounts/callback/facebook",
                params={
                    "code": "auth_code_123",
                    "state": "invalid_state",
                },
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListAccountsEndpoint:
    """Tests for listing user accounts endpoint."""

    def test_list_accounts_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful account listing."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_user_accounts = AsyncMock(return_value=[sample_account])
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "accounts" in data
            assert "total" in data
            assert data["total"] == 1
            assert len(data["accounts"]) == 1

    def test_list_accounts_filter_by_platform(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test listing accounts filtered by platform."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_user_accounts = AsyncMock(return_value=[sample_account])
            mock_service_class.return_value = mock_service

            response = client.get(
                "/social-accounts/",
                params={"platform": "facebook"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert all(
                account["platform"] == Platform.FACEBOOK.value
                for account in data["accounts"]
            )

    def test_list_accounts_empty(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test listing accounts returns empty list."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_user_accounts = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 0
            assert len(data["accounts"]) == 0

    def test_list_accounts_requires_authentication(self, client: TestClient) -> None:
        """Test listing requires authentication."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            side_effect=Exception("Unauthorized"),
        ):
            with pytest.raises(Exception, match="Unauthorized"):
                client.get("/social-accounts/")


class TestGetAccountEndpoint:
    """Tests for getting single account endpoint."""

    def test_get_account_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test successfully getting account details."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/account-123")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "account-123"
            assert data["platform"] == Platform.FACEBOOK.value

    def test_get_account_not_found(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test getting non-existent account."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestVerifyAccountEndpoint:
    """Tests for account verification endpoint."""

    def test_verify_account_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful account verification."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.verify_account = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            response = client.post("/social-accounts/account-123/verify")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_verified"] is True
            assert "message" in data

    def test_verify_account_not_found(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test verification of non-existent account."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            response = client.post("/social-accounts/nonexistent/verify")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_account_verification_fails(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test account verification failure."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.verify_account = AsyncMock(return_value=False)
            mock_service_class.return_value = mock_service

            response = client.post("/social-accounts/account-123/verify")

            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDisconnectAccountEndpoint:
    """Tests for account disconnection endpoint."""

    def test_disconnect_account_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful account disconnection."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.unlink_account = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            response = client.delete("/social-accounts/account-123")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["account_id"] == "account-123"
            assert "message" in data

    def test_disconnect_account_not_found(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test disconnection of non-existent account."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            response = client.delete("/social-accounts/nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_disconnect_account_unauthorized_user(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test disconnection by unauthorized user."""
        sample_account.user_id = "different-user"

        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service_class.return_value = mock_service

            response = client.delete("/social-accounts/account-123")

            assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRefreshTokenEndpoint:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful token refresh."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.refresh_account_tokens = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            response = client.post("/social-accounts/account-123/refresh")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "message" in data

    def test_refresh_token_no_refresh_token(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test refresh fails when no refresh token available."""
        sample_account.refresh_token = None

        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.refresh_account_tokens = AsyncMock(
                side_effect=ValueError("No refresh token")
            )
            mock_service_class.return_value = mock_service

            response = client.post("/social-accounts/account-123/refresh")

            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCompleteIntegrationWorkflows:
    """Tests for complete integration workflows."""

    def test_complete_oauth_flow(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test complete OAuth flow from initiation to callback."""
        # Step 1: Initiate connection
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class:
            mock_oauth = AsyncMock()
            mock_oauth.generate_authorization_url = AsyncMock(
                return_value={
                    "authorization_url": "https://facebook.com/oauth?...",
                    "state": "test_state_token",
                }
            )
            mock_oauth_class.return_value = mock_oauth

            response = client.get("/social-accounts/connect/facebook")
            assert response.status_code == status.HTTP_200_OK
            state = response.json()["state"]

        # Step 2: Handle callback
        with patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.OAuthService"
        ) as mock_oauth_class, patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_account_class:
            mock_oauth = AsyncMock()
            mock_oauth.handle_callback = AsyncMock(
                return_value={
                    "access_token": "test_token",
                    "refresh_token": "test_refresh",
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            mock_account_service = AsyncMock()
            mock_account_service.link_account = AsyncMock(return_value=sample_account)
            mock_account_class.return_value = mock_account_service

            response = client.get(
                "/social-accounts/callback/facebook",
                params={"code": "auth_code", "state": state},
            )
            assert response.status_code == status.HTTP_200_OK

    def test_link_verify_disconnect_workflow(
        self,
        client: TestClient,
        authenticated_user_id: str,
        sample_account: SocialAccount,
    ) -> None:
        """Test complete workflow: link, verify, then disconnect account."""
        account_id = "account-123"

        # Step 1: Verify account
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.verify_account = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            response = client.post(f"/social-accounts/{account_id}/verify")
            assert response.status_code == status.HTTP_200_OK

        # Step 2: Disconnect account
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=sample_account)
            mock_service.unlink_account = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            response = client.delete(f"/social-accounts/{account_id}")
            assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    def test_handles_database_errors(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test API handles database errors gracefully."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_user_accounts = AsyncMock(
                side_effect=Exception("Database error")
            )
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_handles_validation_errors(self, client: TestClient) -> None:
        """Test API handles validation errors."""
        with patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ):
            response = client.get(
                "/social-accounts/callback/facebook",
                params={"state": ""},  # Empty state
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_proper_error_messages(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test API returns descriptive error messages."""
        with patch(
            "src.social_media.routers.social_accounts.require_authentication",
            return_value=authenticated_user_id,
        ), patch(
            "src.social_media.routers.social_accounts.get_database_session"
        ), patch(
            "src.social_media.routers.social_accounts.AccountService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            response = client.get("/social-accounts/nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()


class TestRateLimiting:
    """Tests for rate limiting on endpoints."""

    def test_respects_rate_limits(
        self,
        client: TestClient,
        authenticated_user_id: str,
    ) -> None:
        """Test endpoints respect rate limits."""
        # This would test integration with rate limiting middleware
        # Implementation depends on rate limiting strategy
        pass
