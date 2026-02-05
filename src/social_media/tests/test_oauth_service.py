"""
Tests for OAuth Service.

Comprehensive tests for OAuthService including OAuth flow generation,
callback handling, token refresh, state validation, error handling,
and platform-specific configurations.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.social_media.enums.platform_enums import Platform
from src.social_media.services.oauth_service import OAuthService

logger = logging.getLogger(__name__)


@pytest.fixture
def oauth_service() -> OAuthService:
    """Create OAuthService instance."""
    return OAuthService()


@pytest.fixture
async def oauth_service_with_cleanup(oauth_service: OAuthService):
    """OAuth service fixture with automatic cleanup."""
    yield oauth_service
    await oauth_service.close()


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Create mock HTTP response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "email profile",
    }
    response.text = '{"access_token": "test_access_token"}'
    return response


class TestOAuthServiceInitialization:
    """Tests for OAuth service initialization."""

    def test_init_creates_http_client(self, oauth_service: OAuthService) -> None:
        """Test OAuth service initialization creates HTTP client."""
        assert oauth_service.http_client is not None
        assert isinstance(oauth_service.http_client, httpx.AsyncClient)

    async def test_close_closes_http_client(self, oauth_service: OAuthService) -> None:
        """Test close method closes HTTP client."""
        with patch.object(oauth_service.http_client, "aclose", new=AsyncMock()) as mock_close:
            await oauth_service.close()
            mock_close.assert_called_once()


class TestStateGeneration:
    """Tests for state generation."""

    def test_generate_state_returns_string(self) -> None:
        """Test state generation returns string."""
        state = OAuthService._generate_state()
        assert isinstance(state, str)
        assert len(state) > 20

    def test_generate_state_is_random(self) -> None:
        """Test state generation produces different values."""
        state1 = OAuthService._generate_state()
        state2 = OAuthService._generate_state()
        assert state1 != state2

    def test_generate_state_is_url_safe(self) -> None:
        """Test generated state is URL-safe."""
        state = OAuthService._generate_state()
        assert all(c.isalnum() or c in "-_" for c in state)


class TestPKCEGeneration:
    """Tests for PKCE code generation."""

    def test_generate_code_verifier_returns_string(self) -> None:
        """Test code verifier generation."""
        verifier = OAuthService._generate_code_verifier()
        assert isinstance(verifier, str)
        assert len(verifier) >= 43

    def test_generate_code_verifier_is_random(self) -> None:
        """Test code verifier is unique."""
        verifier1 = OAuthService._generate_code_verifier()
        verifier2 = OAuthService._generate_code_verifier()
        assert verifier1 != verifier2

    def test_generate_code_challenge_from_verifier(self) -> None:
        """Test code challenge generation from verifier."""
        verifier = "test_verifier_string"
        challenge = OAuthService._generate_code_challenge(verifier)
        assert isinstance(challenge, str)
        assert len(challenge) > 0

    def test_generate_code_challenge_is_deterministic(self) -> None:
        """Test same verifier produces same challenge."""
        verifier = "test_verifier"
        challenge1 = OAuthService._generate_code_challenge(verifier)
        challenge2 = OAuthService._generate_code_challenge(verifier)
        assert challenge1 == challenge2


class TestAuthorizationURLGeneration:
    """Tests for authorization URL generation."""

    def test_generate_authorization_url_facebook(
        self, oauth_service: OAuthService
    ) -> None:
        """Test authorization URL generation for Facebook."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.FACEBOOK,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "authorization_url" in result
        assert "state" in result
        assert "code_verifier" in result
        assert "code_challenge" in result

        url = result["authorization_url"]
        assert "facebook.com" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "state=" in url
        assert "code_challenge=" in url

    def test_generate_authorization_url_instagram(
        self, oauth_service: OAuthService
    ) -> None:
        """Test authorization URL generation for Instagram."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.INSTAGRAM,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "instagram.com" in result["authorization_url"]

    def test_generate_authorization_url_twitter(
        self, oauth_service: OAuthService
    ) -> None:
        """Test authorization URL generation for Twitter."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.TWITTER,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "twitter.com" in result["authorization_url"]

    def test_generate_authorization_url_with_custom_scopes(
        self, oauth_service: OAuthService
    ) -> None:
        """Test URL generation with custom scopes."""
        custom_scopes = ["email", "profile"]
        result = oauth_service.generate_authorization_url(
            platform=Platform.FACEBOOK,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
            scopes=custom_scopes,
        )

        url = result["authorization_url"]
        assert "scope=email+profile" in url or "scope=email%20profile" in url

    def test_generate_authorization_url_without_pkce(
        self, oauth_service: OAuthService
    ) -> None:
        """Test URL generation without PKCE."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.FACEBOOK,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
            use_pkce=False,
        )

        assert "code_verifier" not in result
        assert "code_challenge" not in result
        assert "code_challenge=" not in result["authorization_url"]

    def test_generate_authorization_url_uses_default_scopes(
        self, oauth_service: OAuthService
    ) -> None:
        """Test URL generation uses platform default scopes."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.FACEBOOK,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        url = result["authorization_url"]
        assert "scope=" in url

    def test_generate_authorization_url_invalid_platform_config(
        self, oauth_service: OAuthService
    ) -> None:
        """Test error handling for invalid platform."""
        with patch(
            "src.social_media.services.oauth_service.get_platform_config",
            side_effect=ValueError("Invalid platform"),
        ):
            with pytest.raises(ValueError, match="Failed to generate authorization URL"):
                oauth_service.generate_authorization_url(
                    platform=Platform.FACEBOOK,
                    client_id="test_client_id",
                    redirect_uri="https://app.com/callback",
                )


class TestCallbackHandling:
    """Tests for OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_handle_callback_success(
        self, oauth_service: OAuthService, mock_http_response: MagicMock
    ) -> None:
        """Test successful callback handling."""
        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await oauth_service.handle_callback(
                platform=Platform.FACEBOOK,
                code="test_code",
                state="test_state",
                expected_state="test_state",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="https://app.com/callback",
            )

            assert result["access_token"] == "test_access_token"
            assert result["refresh_token"] == "test_refresh_token"
            assert result["expires_in"] == 3600
            assert result["token_type"] == "Bearer"
            assert result["scope"] == "email profile"
            assert "expires_at" in result
            assert isinstance(result["expires_at"], datetime)

    @pytest.mark.asyncio
    async def test_handle_callback_with_pkce(
        self, oauth_service: OAuthService, mock_http_response: MagicMock
    ) -> None:
        """Test callback handling with PKCE verifier."""
        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ) as mock_post:
            await oauth_service.handle_callback(
                platform=Platform.FACEBOOK,
                code="test_code",
                state="test_state",
                expected_state="test_state",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="https://app.com/callback",
                code_verifier="test_verifier",
            )

            call_args = mock_post.call_args
            assert call_args[1]["data"]["code_verifier"] == "test_verifier"

    @pytest.mark.asyncio
    async def test_handle_callback_state_mismatch(
        self, oauth_service: OAuthService
    ) -> None:
        """Test callback fails with state mismatch."""
        with pytest.raises(ValueError, match="State validation failed"):
            await oauth_service.handle_callback(
                platform=Platform.FACEBOOK,
                code="test_code",
                state="wrong_state",
                expected_state="correct_state",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="https://app.com/callback",
            )

    @pytest.mark.asyncio
    async def test_handle_callback_token_exchange_failure(
        self, oauth_service: OAuthService
    ) -> None:
        """Test callback handles token exchange failure."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="Token exchange failed"):
                await oauth_service.handle_callback(
                    platform=Platform.FACEBOOK,
                    code="invalid_code",
                    state="test_state",
                    expected_state="test_state",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    redirect_uri="https://app.com/callback",
                )

    @pytest.mark.asyncio
    async def test_handle_callback_missing_access_token(
        self, oauth_service: OAuthService
    ) -> None:
        """Test callback fails when access token is missing."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"refresh_token": "test_refresh"}

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="No access token in response"):
                await oauth_service.handle_callback(
                    platform=Platform.FACEBOOK,
                    code="test_code",
                    state="test_state",
                    expected_state="test_state",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    redirect_uri="https://app.com/callback",
                )

    @pytest.mark.asyncio
    async def test_handle_callback_calculates_expiration(
        self, oauth_service: OAuthService, mock_http_response: MagicMock
    ) -> None:
        """Test callback calculates expiration timestamp."""
        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await oauth_service.handle_callback(
                platform=Platform.FACEBOOK,
                code="test_code",
                state="test_state",
                expected_state="test_state",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="https://app.com/callback",
            )

            expires_at = result["expires_at"]
            now = datetime.utcnow()
            expected_expiry = now + timedelta(seconds=3600)

            # Allow 5 second tolerance for test execution time
            assert abs((expires_at - expected_expiry).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_handle_callback_network_error(
        self, oauth_service: OAuthService
    ) -> None:
        """Test callback handles network errors."""
        with patch.object(
            oauth_service.http_client,
            "post",
            new=AsyncMock(side_effect=httpx.RequestError("Network error")),
        ):
            with pytest.raises(ValueError, match="Failed to handle OAuth callback"):
                await oauth_service.handle_callback(
                    platform=Platform.FACEBOOK,
                    code="test_code",
                    state="test_state",
                    expected_state="test_state",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    redirect_uri="https://app.com/callback",
                )


class TestTokenRefresh:
    """Tests for token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, oauth_service: OAuthService, mock_http_response: MagicMock
    ) -> None:
        """Test successful token refresh."""
        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await oauth_service.refresh_token(
                platform=Platform.FACEBOOK,
                refresh_token="test_refresh_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result["access_token"] == "test_access_token"
            assert result["refresh_token"] == "test_refresh_token"
            assert result["expires_in"] == 3600
            assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_refresh_token_updates_refresh_token(
        self, oauth_service: OAuthService
    ) -> None:
        """Test refresh updates refresh token when provided."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 7200,
        }

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            result = await oauth_service.refresh_token(
                platform=Platform.FACEBOOK,
                refresh_token="old_refresh_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result["refresh_token"] == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_reuses_refresh_token(
        self, oauth_service: OAuthService
    ) -> None:
        """Test refresh reuses old refresh token if not provided."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 7200,
        }

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            result = await oauth_service.refresh_token(
                platform=Platform.FACEBOOK,
                refresh_token="old_refresh_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result["refresh_token"] == "old_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_unsupported_platform(
        self, oauth_service: OAuthService
    ) -> None:
        """Test refresh fails for platform without refresh support."""
        with patch(
            "src.social_media.services.oauth_service.get_platform_config"
        ) as mock_config:
            mock_config.return_value = MagicMock(supports_refresh_token=False)

            with pytest.raises(ValueError, match="does not support refresh tokens"):
                await oauth_service.refresh_token(
                    platform=Platform.FACEBOOK,
                    refresh_token="test_refresh_token",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, oauth_service: OAuthService) -> None:
        """Test token refresh failure handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="Token refresh failed"):
                await oauth_service.refresh_token(
                    platform=Platform.FACEBOOK,
                    refresh_token="invalid_token",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )

    @pytest.mark.asyncio
    async def test_refresh_token_missing_access_token(
        self, oauth_service: OAuthService
    ) -> None:
        """Test refresh fails when new access token is missing."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"expires_in": 3600}

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="No access token in refresh response"):
                await oauth_service.refresh_token(
                    platform=Platform.FACEBOOK,
                    refresh_token="test_refresh_token",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )


class TestTokenRevocation:
    """Tests for token revocation."""

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, oauth_service: OAuthService) -> None:
        """Test successful token revocation."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            result = await oauth_service.revoke_token(
                platform=Platform.FACEBOOK,
                token="test_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_with_token_type_hint(
        self, oauth_service: OAuthService
    ) -> None:
        """Test revocation with specific token type hint."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ) as mock_post:
            await oauth_service.revoke_token(
                platform=Platform.FACEBOOK,
                token="test_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_type_hint="refresh_token",
            )

            call_args = mock_post.call_args
            assert call_args[1]["data"]["token_type_hint"] == "refresh_token"

    @pytest.mark.asyncio
    async def test_revoke_token_accepts_204(self, oauth_service: OAuthService) -> None:
        """Test revocation accepts 204 No Content response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            result = await oauth_service.revoke_token(
                platform=Platform.FACEBOOK,
                token="test_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_non_success_status(
        self, oauth_service: OAuthService
    ) -> None:
        """Test revocation handles non-success status codes."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400

        with patch.object(
            oauth_service.http_client, "post", new=AsyncMock(return_value=mock_response)
        ):
            # Should still return True but log warning
            result = await oauth_service.revoke_token(
                platform=Platform.FACEBOOK,
                token="test_token",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_network_error(
        self, oauth_service: OAuthService
    ) -> None:
        """Test revocation handles network errors."""
        with patch.object(
            oauth_service.http_client,
            "post",
            new=AsyncMock(side_effect=httpx.RequestError("Network error")),
        ):
            with pytest.raises(ValueError, match="Failed to revoke token"):
                await oauth_service.revoke_token(
                    platform=Platform.FACEBOOK,
                    token="test_token",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )


class TestStateValidation:
    """Tests for state validation."""

    def test_validate_state_matching(self, oauth_service: OAuthService) -> None:
        """Test state validation with matching states."""
        state = "test_state_12345"
        assert oauth_service.validate_state(state, state) is True

    def test_validate_state_mismatch(self, oauth_service: OAuthService) -> None:
        """Test state validation with mismatching states."""
        assert oauth_service.validate_state("state1", "state2") is False

    def test_validate_state_empty_strings(self, oauth_service: OAuthService) -> None:
        """Test state validation with empty strings."""
        assert oauth_service.validate_state("", "") is True

    def test_validate_state_timing_attack_resistant(
        self, oauth_service: OAuthService
    ) -> None:
        """Test state validation uses timing-attack resistant comparison."""
        # This test verifies that secrets.compare_digest is used
        with patch("secrets.compare_digest", return_value=True) as mock_compare:
            oauth_service.validate_state("state1", "state2")
            mock_compare.assert_called_once_with("state1", "state2")


class TestPlatformSpecificConfigurations:
    """Tests for platform-specific OAuth configurations."""

    @pytest.mark.parametrize(
        "platform",
        [
            Platform.FACEBOOK,
            Platform.INSTAGRAM,
            Platform.TWITTER,
            Platform.TIKTOK,
            Platform.LINKEDIN,
            Platform.YOUTUBE,
        ],
    )
    def test_generate_url_for_all_platforms(
        self, oauth_service: OAuthService, platform: Platform
    ) -> None:
        """Test URL generation works for all platforms."""
        result = oauth_service.generate_authorization_url(
            platform=platform,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "authorization_url" in result
        assert "state" in result
        assert len(result["authorization_url"]) > 0

    def test_facebook_uses_correct_endpoints(
        self, oauth_service: OAuthService
    ) -> None:
        """Test Facebook uses correct OAuth endpoints."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.FACEBOOK,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "facebook.com" in result["authorization_url"]
        assert "/oauth" in result["authorization_url"]

    def test_twitter_uses_correct_endpoints(self, oauth_service: OAuthService) -> None:
        """Test Twitter uses correct OAuth endpoints."""
        result = oauth_service.generate_authorization_url(
            platform=Platform.TWITTER,
            client_id="test_client_id",
            redirect_uri="https://app.com/callback",
        )

        assert "twitter.com" in result["authorization_url"]
        assert "/oauth2" in result["authorization_url"]
