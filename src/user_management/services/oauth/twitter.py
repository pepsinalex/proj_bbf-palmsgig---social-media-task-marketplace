"""Twitter OAuth 2.0 provider implementation."""

import logging
from typing import Any

from src.user_management.services.oauth.base import BaseOAuthProvider, OAuthUserInfo

logger = logging.getLogger(__name__)


class TwitterOAuthProvider(BaseOAuthProvider):
    """
    Twitter OAuth 2.0 provider implementation.

    Implements Twitter-specific OAuth flow with API v2.
    Handles user info retrieval from Twitter API v2.
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "twitter"

    @property
    def authorization_url(self) -> str:
        """Return Twitter's OAuth authorization endpoint."""
        return "https://twitter.com/i/oauth2/authorize"

    @property
    def token_url(self) -> str:
        """Return Twitter's OAuth token endpoint."""
        return "https://api.twitter.com/2/oauth2/token"

    @property
    def user_info_url(self) -> str:
        """Return Twitter's user info endpoint."""
        return "https://api.twitter.com/2/users/me"

    @property
    def default_scopes(self) -> list[str]:
        """Return default scopes for Twitter OAuth."""
        return ["tweet.read", "users.read"]

    async def generate_auth_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        **extra_params: Any,
    ) -> tuple[str, str]:
        """
        Generate OAuth authorization URL for user redirect with Twitter-specific params.

        Args:
            state: Optional state parameter (generated if not provided)
            scopes: Optional list of OAuth scopes (uses default if not provided)
            **extra_params: Additional provider-specific parameters

        Returns:
            Tuple of (authorization_url, state)
        """
        import secrets

        code_verifier = secrets.token_urlsafe(32)
        code_challenge = code_verifier

        extra_params["code_challenge"] = code_challenge
        extra_params["code_challenge_method"] = "plain"

        return await super().generate_auth_url(state, scopes, **extra_params)

    async def _parse_user_info(self, user_data: dict[str, Any]) -> OAuthUserInfo:
        """
        Parse Twitter user data into OAuthUserInfo model.

        Args:
            user_data: Raw user data from Twitter

        Returns:
            OAuthUserInfo with normalized Twitter user data
        """
        logger.debug(
            "Parsing Twitter user info",
            extra={"user_id": user_data.get("data", {}).get("id")},
        )

        data = user_data.get("data", {})

        profile_url = f"https://twitter.com/{data.get('username')}" if "username" in data else None

        return OAuthUserInfo(
            provider_user_id=data["id"],
            email=None,
            name=data.get("name"),
            avatar_url=data.get("profile_image_url"),
            profile_url=profile_url,
            raw_data=user_data,
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Fetch user information using access token with Twitter-specific fields.

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
                params={"user.fields": "id,name,username,profile_image_url"},
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

        except Exception as e:
            logger.error(
                f"Failed to fetch user info",
                extra={"provider": self.provider_name, "error": str(e)},
                exc_info=True,
            )
            raise


from typing import Optional
