"""Google OAuth 2.0 provider implementation."""

import logging
from typing import Any

from src.user_management.services.oauth.base import BaseOAuthProvider, OAuthUserInfo

logger = logging.getLogger(__name__)


class GoogleOAuthProvider(BaseOAuthProvider):
    """
    Google OAuth 2.0 provider implementation.

    Implements Google-specific OAuth flow with email and profile scopes.
    Handles user info retrieval from Google People API.
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "google"

    @property
    def authorization_url(self) -> str:
        """Return Google's OAuth authorization endpoint."""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_url(self) -> str:
        """Return Google's OAuth token endpoint."""
        return "https://oauth2.googleapis.com/token"

    @property
    def user_info_url(self) -> str:
        """Return Google's user info endpoint."""
        return "https://www.googleapis.com/oauth2/v2/userinfo"

    @property
    def default_scopes(self) -> list[str]:
        """Return default scopes for Google OAuth."""
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

    async def _parse_user_info(self, user_data: dict[str, Any]) -> OAuthUserInfo:
        """
        Parse Google user data into OAuthUserInfo model.

        Args:
            user_data: Raw user data from Google

        Returns:
            OAuthUserInfo with normalized Google user data
        """
        logger.debug(
            "Parsing Google user info",
            extra={"user_id": user_data.get("id"), "has_email": "email" in user_data},
        )

        return OAuthUserInfo(
            provider_user_id=user_data["id"],
            email=user_data.get("email"),
            name=user_data.get("name"),
            avatar_url=user_data.get("picture"),
            profile_url=None,
            raw_data=user_data,
        )
