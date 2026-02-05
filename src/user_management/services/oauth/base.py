"""Base OAuth provider abstract class for social media authentication."""

import hashlib
import logging
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OAuthUserInfo(BaseModel):
    """OAuth user information model."""

    provider_user_id: str = Field(..., description="User ID from OAuth provider")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar/profile picture URL")
    profile_url: Optional[str] = Field(None, description="User profile URL")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw response data")


class OAuthTokenResponse(BaseModel):
    """OAuth token response model."""

    access_token: str = Field(..., description="OAuth access token")
    token_type: str = Field(..., description="Token type (usually 'Bearer')")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token for renewing access")
    scope: Optional[str] = Field(None, description="OAuth scopes granted")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw token response")


class BaseOAuthProvider(ABC):
    """
    Abstract base class for OAuth 2.0 providers.

    Defines the interface and common functionality for all OAuth providers.
    Subclasses must implement provider-specific endpoints and user info parsing.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize OAuth provider.

        Args:
            client_id: OAuth application client ID
            client_secret: OAuth application client secret
            redirect_uri: Callback URL for OAuth flow
            http_client: Optional httpx client for making API requests
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._http_client = http_client
        logger.info(
            f"Initialized {self.__class__.__name__}",
            extra={"client_id": client_id, "redirect_uri": redirect_uri},
        )

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the OAuth provider name (e.g., 'google', 'facebook')."""

    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """Return the OAuth authorization endpoint URL."""

    @property
    @abstractmethod
    def token_url(self) -> str:
        """Return the OAuth token endpoint URL."""

    @property
    @abstractmethod
    def user_info_url(self) -> str:
        """Return the URL for fetching user information."""

    @property
    @abstractmethod
    def default_scopes(self) -> list[str]:
        """Return the default OAuth scopes to request."""

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API requests."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def generate_state(self) -> str:
        """
        Generate a cryptographically secure state parameter.

        Returns:
            Random state string for CSRF protection
        """
        return secrets.token_urlsafe(32)

    def validate_state(self, state: str, expected_state: str) -> bool:
        """
        Validate OAuth state parameter against expected value.

        Args:
            state: State parameter received from OAuth provider
            expected_state: Expected state value stored before redirect

        Returns:
            True if state is valid, False otherwise
        """
        if not state or not expected_state:
            logger.warning(
                "State validation failed: missing state",
                extra={"state_present": bool(state), "expected_state_present": bool(expected_state)},
            )
            return False

        is_valid = secrets.compare_digest(state, expected_state)
        if not is_valid:
            logger.warning("State validation failed: mismatch", extra={"provider": self.provider_name})
        return is_valid

    async def generate_auth_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        **extra_params: Any,
    ) -> tuple[str, str]:
        """
        Generate OAuth authorization URL for user redirect.

        Args:
            state: Optional state parameter (generated if not provided)
            scopes: Optional list of OAuth scopes (uses default if not provided)
            **extra_params: Additional provider-specific parameters

        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = self.generate_state()

        if scopes is None:
            scopes = self.default_scopes

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            **extra_params,
        }

        auth_url = f"{self.authorization_url}?{urlencode(params)}"
        logger.info(
            f"Generated auth URL for {self.provider_name}",
            extra={"state": state, "scopes": scopes},
        )

        return auth_url, state

    async def handle_callback(self, code: str, state: Optional[str] = None) -> OAuthTokenResponse:
        """
        Handle OAuth callback and exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth provider
            state: Optional state parameter for validation

        Returns:
            OAuthTokenResponse with access token and metadata

        Raises:
            httpx.HTTPError: If token exchange fails
            ValueError: If response is invalid
        """
        logger.info(
            f"Handling OAuth callback for {self.provider_name}",
            extra={"code_length": len(code) if code else 0},
        )

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info(
                f"Successfully exchanged code for token",
                extra={"provider": self.provider_name, "has_refresh": "refresh_token" in token_data},
            )

            return OAuthTokenResponse(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
                raw_data=token_data,
            )

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to exchange code for token",
                extra={"provider": self.provider_name, "error": str(e)},
                exc_info=True,
            )
            raise

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Fetch user information using access token.

        Args:
            access_token: Valid OAuth access token

        Returns:
            OAuthUserInfo with user profile data

        Raises:
            httpx.HTTPError: If user info request fails
            ValueError: If response is invalid
        """
        logger.info(f"Fetching user info for {self.provider_name}")

        try:
            response = await self.http_client.get(
                self.user_info_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            user_data = response.json()

            user_info = await self._parse_user_info(user_data)
            logger.info(
                f"Successfully fetched user info",
                extra={"provider": self.provider_name, "user_id": user_info.provider_user_id},
            )
            return user_info

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch user info",
                extra={"provider": self.provider_name, "error": str(e)},
                exc_info=True,
            )
            raise

    @abstractmethod
    async def _parse_user_info(self, user_data: dict[str, Any]) -> OAuthUserInfo:
        """
        Parse provider-specific user data into OAuthUserInfo model.

        Args:
            user_data: Raw user data from provider

        Returns:
            OAuthUserInfo with normalized user data
        """

    async def refresh_token(self, refresh_token: str) -> OAuthTokenResponse:
        """
        Refresh OAuth access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            OAuthTokenResponse with new access token

        Raises:
            httpx.HTTPError: If token refresh fails
            ValueError: If response is invalid
        """
        logger.info(f"Refreshing token for {self.provider_name}")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            response = await self.http_client.post(
                self.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info(
                f"Successfully refreshed token",
                extra={"provider": self.provider_name},
            )

            return OAuthTokenResponse(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token", refresh_token),
                scope=token_data.get("scope"),
                raw_data=token_data,
            )

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to refresh token",
                extra={"provider": self.provider_name, "error": str(e)},
                exc_info=True,
            )
            raise

    async def close(self) -> None:
        """Close HTTP client if it was created by this instance."""
        if self._http_client is not None:
            await self._http_client.aclose()
            logger.debug(f"Closed HTTP client for {self.provider_name}")
