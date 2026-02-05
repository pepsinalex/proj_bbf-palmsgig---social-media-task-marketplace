"""
OAuth 2.0 service for social media platform authentication.

This module implements OAuth 2.0 flows for major social media platforms including
Facebook, Instagram, Twitter, TikTok, LinkedIn, and YouTube. Provides secure
authentication, token exchange, refresh, and revocation with state validation
and PKCE support.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from src.shared.config import get_settings
from src.social_media.enums.platform_enums import Platform, get_platform_config

logger = logging.getLogger(__name__)
settings = get_settings()


class OAuthService:
    """
    OAuth 2.0 service for social media authentication.

    Handles OAuth flows including authorization URL generation, callback handling,
    token refresh, and revocation for all supported platforms. Implements security
    best practices including state validation and PKCE.
    """

    def __init__(self) -> None:
        """Initialize OAuth service with HTTP client."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("OAuth service initialized")

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self.http_client.aclose()
        logger.debug("OAuth service HTTP client closed")

    @staticmethod
    def _generate_state() -> str:
        """
        Generate secure random state for OAuth flow.

        Returns:
            Secure random state string

        Example:
            >>> state = OAuthService._generate_state()
            >>> len(state) > 20
            True
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def _generate_code_verifier() -> str:
        """
        Generate PKCE code verifier.

        Returns:
            Base64 URL-safe code verifier string

        Example:
            >>> verifier = OAuthService._generate_code_verifier()
            >>> len(verifier) >= 43
            True
        """
        return secrets.token_urlsafe(64)

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.

        Args:
            code_verifier: Code verifier string

        Returns:
            Base64 URL-safe code challenge

        Example:
            >>> verifier = "test_verifier"
            >>> challenge = OAuthService._generate_code_challenge(verifier)
            >>> len(challenge) > 0
            True
        """
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return secrets.token_urlsafe(len(digest))[:43]

    def generate_authorization_url(
        self,
        platform: Platform,
        client_id: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
        use_pkce: bool = True,
    ) -> dict[str, str]:
        """
        Generate OAuth authorization URL for platform.

        Args:
            platform: Social media platform
            client_id: OAuth client ID
            redirect_uri: Callback redirect URI
            scopes: OAuth scopes (uses platform defaults if None)
            use_pkce: Whether to use PKCE flow

        Returns:
            Dictionary containing authorization URL, state, and PKCE parameters

        Raises:
            ValueError: If platform configuration is invalid

        Example:
            >>> service = OAuthService()
            >>> result = service.generate_authorization_url(
            ...     Platform.FACEBOOK, "client_id", "https://app.com/callback"
            ... )
            >>> "authorization_url" in result
            True
        """
        try:
            config = get_platform_config(platform)

            state = self._generate_state()
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "response_type": "code",
            }

            if scopes:
                scope_string = " ".join(scopes)
            else:
                scope_string = " ".join(config.default_scopes)

            params["scope"] = scope_string

            code_verifier = None
            code_challenge = None

            if use_pkce:
                code_verifier = self._generate_code_verifier()
                code_challenge = self._generate_code_challenge(code_verifier)
                params["code_challenge"] = code_challenge
                params["code_challenge_method"] = "S256"

            authorization_url = f"{config.oauth_authorize_url}?{urlencode(params)}"

            result = {
                "authorization_url": authorization_url,
                "state": state,
            }

            if code_verifier:
                result["code_verifier"] = code_verifier

            if code_challenge:
                result["code_challenge"] = code_challenge

            logger.info(
                "Authorization URL generated",
                extra={
                    "platform": platform.value,
                    "use_pkce": use_pkce,
                    "scopes": scope_string,
                },
            )

            return result

        except Exception as exc:
            logger.error(
                "Failed to generate authorization URL",
                extra={
                    "platform": platform.value,
                    "error": str(exc),
                },
            )
            raise ValueError(f"Failed to generate authorization URL: {str(exc)}") from exc

    async def handle_callback(
        self,
        platform: Platform,
        code: str,
        state: str,
        expected_state: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> dict[str, any]:
        """
        Handle OAuth callback and exchange code for tokens.

        Args:
            platform: Social media platform
            code: Authorization code from callback
            state: State parameter from callback
            expected_state: Expected state value for validation
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Callback redirect URI
            code_verifier: PKCE code verifier (if PKCE was used)

        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If state validation fails or token exchange fails

        Example:
            >>> service = OAuthService()
            >>> tokens = await service.handle_callback(
            ...     Platform.FACEBOOK, "auth_code", "state123", "state123",
            ...     "client_id", "client_secret", "https://app.com/callback"
            ... )
            >>> "access_token" in tokens
            True
        """
        try:
            if state != expected_state:
                logger.error(
                    "State validation failed",
                    extra={
                        "platform": platform.value,
                        "expected_state": expected_state,
                        "received_state": state,
                    },
                )
                raise ValueError("State validation failed - possible CSRF attack")

            config = get_platform_config(platform)

            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            if code_verifier:
                token_data["code_verifier"] = code_verifier

            response = await self.http_client.post(
                config.oauth_token_url,
                data=token_data,
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error(
                    "Token exchange failed",
                    extra={
                        "platform": platform.value,
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                raise ValueError(f"Token exchange failed: {response.text}")

            token_response = response.json()

            access_token = token_response.get("access_token")
            if not access_token:
                logger.error(
                    "No access token in response",
                    extra={
                        "platform": platform.value,
                        "response_keys": list(token_response.keys()),
                    },
                )
                raise ValueError("No access token in response")

            expires_in = token_response.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            result = {
                "access_token": access_token,
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": expires_in,
                "expires_at": expires_at,
                "token_type": token_response.get("token_type", "Bearer"),
                "scope": token_response.get("scope"),
            }

            logger.info(
                "OAuth callback handled successfully",
                extra={
                    "platform": platform.value,
                    "has_refresh_token": result["refresh_token"] is not None,
                    "expires_in": expires_in,
                },
            )

            return result

        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to handle OAuth callback",
                extra={
                    "platform": platform.value,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise ValueError(f"Failed to handle OAuth callback: {str(exc)}") from exc

    async def refresh_token(
        self,
        platform: Platform,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> dict[str, any]:
        """
        Refresh OAuth access token.

        Args:
            platform: Social media platform
            refresh_token: Refresh token string
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            Dictionary containing new access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If token refresh fails

        Example:
            >>> service = OAuthService()
            >>> tokens = await service.refresh_token(
            ...     Platform.FACEBOOK, "refresh_token",
            ...     "client_id", "client_secret"
            ... )
            >>> "access_token" in tokens
            True
        """
        try:
            config = get_platform_config(platform)

            if not config.supports_refresh_token:
                logger.error(
                    "Platform does not support refresh tokens",
                    extra={"platform": platform.value},
                )
                raise ValueError(f"{platform.value} does not support refresh tokens")

            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            response = await self.http_client.post(
                config.oauth_token_url,
                data=refresh_data,
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error(
                    "Token refresh failed",
                    extra={
                        "platform": platform.value,
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                raise ValueError(f"Token refresh failed: {response.text}")

            token_response = response.json()

            access_token = token_response.get("access_token")
            if not access_token:
                logger.error(
                    "No access token in refresh response",
                    extra={
                        "platform": platform.value,
                        "response_keys": list(token_response.keys()),
                    },
                )
                raise ValueError("No access token in refresh response")

            expires_in = token_response.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            result = {
                "access_token": access_token,
                "refresh_token": token_response.get("refresh_token", refresh_token),
                "expires_in": expires_in,
                "expires_at": expires_at,
                "token_type": token_response.get("token_type", "Bearer"),
                "scope": token_response.get("scope"),
            }

            logger.info(
                "Token refreshed successfully",
                extra={
                    "platform": platform.value,
                    "has_new_refresh_token": token_response.get("refresh_token") is not None,
                    "expires_in": expires_in,
                },
            )

            return result

        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to refresh token",
                extra={
                    "platform": platform.value,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise ValueError(f"Failed to refresh token: {str(exc)}") from exc

    async def revoke_token(
        self,
        platform: Platform,
        token: str,
        client_id: str,
        client_secret: str,
        token_type_hint: str = "access_token",
    ) -> bool:
        """
        Revoke OAuth access or refresh token.

        Args:
            platform: Social media platform
            token: Token to revoke
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_type_hint: Type of token ("access_token" or "refresh_token")

        Returns:
            True if revocation succeeded

        Raises:
            ValueError: If token revocation fails

        Example:
            >>> service = OAuthService()
            >>> success = await service.revoke_token(
            ...     Platform.FACEBOOK, "token",
            ...     "client_id", "client_secret"
            ... )
            >>> success
            True
        """
        try:
            config = get_platform_config(platform)

            revoke_url = getattr(config, "oauth_revoke_url", None)
            if not revoke_url:
                revoke_url = config.oauth_token_url.replace("/token", "/revoke")

            revoke_data = {
                "token": token,
                "client_id": client_id,
                "client_secret": client_secret,
                "token_type_hint": token_type_hint,
            }

            response = await self.http_client.post(
                revoke_url,
                data=revoke_data,
                headers={"Accept": "application/json"},
            )

            if response.status_code not in [200, 204]:
                logger.warning(
                    "Token revocation returned non-success status",
                    extra={
                        "platform": platform.value,
                        "status_code": response.status_code,
                        "token_type_hint": token_type_hint,
                    },
                )

            logger.info(
                "Token revoked successfully",
                extra={
                    "platform": platform.value,
                    "token_type_hint": token_type_hint,
                },
            )

            return True

        except Exception as exc:
            logger.error(
                "Failed to revoke token",
                extra={
                    "platform": platform.value,
                    "token_type_hint": token_type_hint,
                    "error": str(exc),
                },
            )
            raise ValueError(f"Failed to revoke token: {str(exc)}") from exc

    def validate_state(self, received_state: str, expected_state: str) -> bool:
        """
        Validate OAuth state parameter.

        Args:
            received_state: State received from callback
            expected_state: Expected state value

        Returns:
            True if states match

        Example:
            >>> service = OAuthService()
            >>> service.validate_state("abc123", "abc123")
            True
        """
        is_valid = secrets.compare_digest(received_state, expected_state)

        if not is_valid:
            logger.warning(
                "State validation failed",
                extra={
                    "expected_state": expected_state,
                    "received_state": received_state,
                },
            )

        return is_valid
