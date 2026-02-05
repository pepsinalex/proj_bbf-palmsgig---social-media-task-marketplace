"""Facebook OAuth 2.0 provider implementation."""

import logging
from typing import Any

from src.user_management.services.oauth.base import BaseOAuthProvider, OAuthUserInfo

logger = logging.getLogger(__name__)


class FacebookOAuthProvider(BaseOAuthProvider):
    """
    Facebook OAuth 2.0 provider implementation.

    Implements Facebook-specific OAuth flow with Graph API integration.
    Handles user info retrieval from Facebook Graph API.
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "facebook"

    @property
    def authorization_url(self) -> str:
        """Return Facebook's OAuth authorization endpoint."""
        return "https://www.facebook.com/v18.0/dialog/oauth"

    @property
    def token_url(self) -> str:
        """Return Facebook's OAuth token endpoint."""
        return "https://graph.facebook.com/v18.0/oauth/access_token"

    @property
    def user_info_url(self) -> str:
        """Return Facebook's user info endpoint."""
        return "https://graph.facebook.com/v18.0/me"

    @property
    def default_scopes(self) -> list[str]:
        """Return default scopes for Facebook OAuth."""
        return ["email", "public_profile"]

    async def _parse_user_info(self, user_data: dict[str, Any]) -> OAuthUserInfo:
        """
        Parse Facebook user data into OAuthUserInfo model.

        Args:
            user_data: Raw user data from Facebook

        Returns:
            OAuthUserInfo with normalized Facebook user data
        """
        logger.debug(
            "Parsing Facebook user info",
            extra={"user_id": user_data.get("id"), "has_email": "email" in user_data},
        )

        avatar_url = None
        if "picture" in user_data and isinstance(user_data["picture"], dict):
            avatar_url = user_data["picture"].get("data", {}).get("url")

        profile_url = f"https://www.facebook.com/{user_data['id']}" if "id" in user_data else None

        return OAuthUserInfo(
            provider_user_id=user_data["id"],
            email=user_data.get("email"),
            name=user_data.get("name"),
            avatar_url=avatar_url,
            profile_url=profile_url,
            raw_data=user_data,
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Fetch user information using access token with Facebook-specific fields.

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
                params={"fields": "id,name,email,picture", "access_token": access_token},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            user_data = response.json()

            user_info = await self._parse_user_info(user_data)
            logger.info(
                f"Successfully fetched user info",
                extra={"provider": self.provider_name, "user_id": user_info.provider_user_id},
            )
            return user_info

        except Exception as e:
            logger.error(
                f"Failed to fetch user info",
                extra={"provider": self.provider_name, "error": str(e)},
                exc_info=True,
            )
            raise
