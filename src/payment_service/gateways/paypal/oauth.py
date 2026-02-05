"""
PayPal OAuth 2.0 Authentication Handler.

This module provides PayPal OAuth authentication with authorization URL generation,
token exchange, token refresh, and account linking capabilities.
"""

import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from src.payment_service.gateways.base import GatewayError, ValidationError

logger = logging.getLogger(__name__)

PAYPAL_AUTH_BASE_SANDBOX = "https://www.sandbox.paypal.com"
PAYPAL_AUTH_BASE_LIVE = "https://www.paypal.com"


class PayPalOAuth:
    """
    PayPal OAuth 2.0 authentication handler.

    Manages OAuth flow including authorization, token exchange, and refresh.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        sandbox: bool = True,
    ):
        """
        Initialize PayPal OAuth handler.

        Args:
            client_id: PayPal client ID
            client_secret: PayPal client secret
            redirect_uri: OAuth redirect URI
            sandbox: Whether to use sandbox environment
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.sandbox = sandbox
        self.auth_base_url = PAYPAL_AUTH_BASE_SANDBOX if sandbox else PAYPAL_AUTH_BASE_LIVE
        self.api_base_url = (
            "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate PayPal authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL string
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid profile email",
        }

        if state:
            params["state"] = state

        auth_url = f"{self.auth_base_url}/signin/authorize"
        url_with_params = f"{auth_url}?{urlencode(params)}"

        logger.info(
            "Generated PayPal authorization URL",
            extra={"redirect_uri": self.redirect_uri},
        )

        return url_with_params

    async def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response with access_token and refresh_token

        Raises:
            GatewayError: If token exchange fails
            ValidationError: If code is invalid
        """
        if not code or not code.strip():
            raise ValidationError(
                "Authorization code is required",
                code="MISSING_AUTH_CODE",
            )

        client = await self._get_client()
        auth = (self.client_id, self.client_secret)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        try:
            response = await client.post(
                f"{self.api_base_url}/v1/oauth2/token",
                auth=auth,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info(
                "Successfully exchanged authorization code for token",
                extra={
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                },
            )

            return token_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to exchange authorization code",
                extra={"status_code": e.response.status_code, "error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "Failed to exchange authorization code",
                code="TOKEN_EXCHANGE_FAILED",
                status_code=e.response.status_code,
            )
        except Exception as e:
            logger.error(
                "Unexpected error during token exchange",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "Token exchange failed",
                code="TOKEN_EXCHANGE_ERROR",
                error=str(e),
            )

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous authorization

        Returns:
            New token response with access_token

        Raises:
            GatewayError: If token refresh fails
            ValidationError: If refresh_token is invalid
        """
        if not refresh_token or not refresh_token.strip():
            raise ValidationError(
                "Refresh token is required",
                code="MISSING_REFRESH_TOKEN",
            )

        client = await self._get_client()
        auth = (self.client_id, self.client_secret)

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            response = await client.post(
                f"{self.api_base_url}/v1/oauth2/token",
                auth=auth,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info(
                "Successfully refreshed access token",
                extra={"expires_in": token_data.get("expires_in")},
            )

            return token_data

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to refresh access token",
                extra={"status_code": e.response.status_code, "error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "Failed to refresh access token",
                code="TOKEN_REFRESH_FAILED",
                status_code=e.response.status_code,
            )
        except Exception as e:
            logger.error(
                "Unexpected error during token refresh",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "Token refresh failed",
                code="TOKEN_REFRESH_ERROR",
                error=str(e),
            )

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            access_token: Access token from OAuth flow

        Returns:
            User information dict

        Raises:
            GatewayError: If user info retrieval fails
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.api_base_url}/v1/identity/oauth2/userinfo",
                params={"schema": "paypalv1.1"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            user_info = response.json()

            logger.info(
                "Successfully retrieved user info",
                extra={"user_id": user_info.get("user_id")},
            )

            return user_info

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to retrieve user info",
                extra={"status_code": e.response.status_code, "error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "Failed to retrieve user information",
                code="USER_INFO_FAILED",
                status_code=e.response.status_code,
            )
        except Exception as e:
            logger.error(
                "Unexpected error retrieving user info",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise GatewayError(
                "User info retrieval failed",
                code="USER_INFO_ERROR",
                error=str(e),
            )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
