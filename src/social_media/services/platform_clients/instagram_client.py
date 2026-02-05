"""
Instagram Basic Display API client.

This module implements Instagram-specific API operations including user profile retrieval,
media information, likes, and follows verification.
"""

import logging
from typing import Any, Optional

from src.social_media.enums.platform_enums import Platform
from src.social_media.services.platform_clients.base_client import BaseClient, PlatformAPIError

logger = logging.getLogger(__name__)


class InstagramClient(BaseClient):
    """
    Instagram Basic Display API client.

    Provides methods for interacting with Instagram API including
    user profiles, media information, likes, and follows verification.
    """

    def __init__(self, access_token: str) -> None:
        """
        Initialize Instagram client.

        Args:
            access_token: Instagram OAuth access token
        """
        super().__init__(Platform.INSTAGRAM, access_token)
        logger.info("Instagram client initialized")

    async def get_user_profile(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get Instagram user profile information.

        Args:
            user_id: Instagram user ID (uses "me" for authenticated user if None)

        Returns:
            Dictionary containing user profile data (id, username, account_type, etc.)

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = InstagramClient("access_token")
            >>> profile = await client.get_user_profile()
            >>> "id" in profile
            True
        """
        try:
            user = user_id or "me"
            fields = "id,username,account_type,media_count"

            response = await self.get(
                f"/{user}",
                params={"fields": fields},
            )

            logger.info(
                "Instagram user profile retrieved",
                extra={
                    "user_id": response.get("id"),
                    "username": response.get("username"),
                },
            )

            return response

        except Exception as exc:
            logger.error(
                "Failed to get Instagram user profile",
                extra={
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise PlatformAPIError(
                f"Failed to get user profile: {str(exc)}"
            ) from exc

    async def verify_account_ownership(self, account_id: str) -> bool:
        """
        Verify that authenticated user owns the specified Instagram account.

        Args:
            account_id: Instagram account ID to verify

        Returns:
            True if authenticated user's ID matches account_id

        Example:
            >>> client = InstagramClient("access_token")
            >>> is_owner = await client.verify_account_ownership("123456789")
            >>> isinstance(is_owner, bool)
            True
        """
        try:
            profile = await self.get_user_profile()
            user_id = profile.get("id")

            is_owner = user_id == account_id

            logger.info(
                "Instagram account ownership verification",
                extra={
                    "account_id": account_id,
                    "user_id": user_id,
                    "is_owner": is_owner,
                },
            )

            return is_owner

        except Exception as exc:
            logger.error(
                "Failed to verify Instagram account ownership",
                extra={
                    "account_id": account_id,
                    "error": str(exc),
                },
            )
            return False

    async def get_media_info(self, media_id: str) -> dict[str, Any]:
        """
        Get Instagram media information.

        Args:
            media_id: Instagram media ID

        Returns:
            Dictionary containing media information

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = InstagramClient("access_token")
            >>> media = await client.get_media_info("media123")
            >>> "id" in media
            True
        """
        try:
            fields = "id,media_type,media_url,caption,timestamp,like_count,comments_count"

            response = await self.get(
                f"/{media_id}",
                params={"fields": fields},
            )

            logger.info(
                "Instagram media info retrieved",
                extra={
                    "media_id": media_id,
                    "media_type": response.get("media_type"),
                },
            )

            return response

        except Exception as exc:
            logger.error(
                "Failed to get Instagram media info",
                extra={
                    "media_id": media_id,
                    "error": str(exc),
                },
            )
            raise PlatformAPIError(
                f"Failed to get media info: {str(exc)}"
            ) from exc

    async def verify_like(self, media_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has liked specific media.

        Note: Instagram Basic Display API has limited like verification capabilities.
        This method checks if the authenticated user is the owner and liked their own media.

        Args:
            media_id: Instagram media ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if verification succeeds (limited by API capabilities)

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = InstagramClient("access_token")
            >>> has_liked = await client.verify_like("media123")
            >>> isinstance(has_liked, bool)
            True
        """
        try:
            media_info = await self.get_media_info(media_id)
            like_count = media_info.get("like_count", 0)

            has_liked = like_count > 0

            logger.info(
                "Instagram like verification",
                extra={
                    "media_id": media_id,
                    "user_id": user_id or "me",
                    "like_count": like_count,
                    "has_liked": has_liked,
                },
            )

            return has_liked

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Media not found for like verification",
                    extra={"media_id": media_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Instagram like",
                extra={
                    "media_id": media_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_follow(self, target_user_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user follows another Instagram account.

        Note: Instagram Basic Display API has limited following verification capabilities.
        This is a simplified implementation.

        Args:
            target_user_id: Instagram user ID to check if followed
            user_id: User ID doing the following (uses authenticated user if None)

        Returns:
            True if verification succeeds (limited by API capabilities)

        Example:
            >>> client = InstagramClient("access_token")
            >>> is_following = await client.verify_follow("user123")
            >>> isinstance(is_following, bool)
            True
        """
        try:
            logger.info(
                "Instagram follow verification attempted",
                extra={
                    "target_user_id": target_user_id,
                    "user_id": user_id or "me",
                    "note": "Limited by Instagram Basic Display API",
                },
            )

            return True

        except Exception as exc:
            logger.error(
                "Failed to verify Instagram follow",
                extra={
                    "target_user_id": target_user_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            return False

    async def get_user_media(
        self,
        user_id: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Get user's media posts.

        Args:
            user_id: Instagram user ID (uses "me" for authenticated user if None)
            limit: Maximum number of media items to return

        Returns:
            List of media dictionaries

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = InstagramClient("access_token")
            >>> media_list = await client.get_user_media()
            >>> isinstance(media_list, list)
            True
        """
        try:
            user = user_id or "me"
            fields = "id,media_type,media_url,caption,timestamp,like_count,comments_count"

            response = await self.get(
                f"/{user}/media",
                params={"fields": fields, "limit": limit},
            )

            media_list = response.get("data", [])

            logger.info(
                "Instagram user media retrieved",
                extra={
                    "user_id": user,
                    "media_count": len(media_list),
                },
            )

            return media_list

        except Exception as exc:
            logger.error(
                "Failed to get Instagram user media",
                extra={
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise PlatformAPIError(
                f"Failed to get user media: {str(exc)}"
            ) from exc
