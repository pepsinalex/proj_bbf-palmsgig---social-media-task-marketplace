"""
Facebook Graph API client.

This module implements Facebook-specific API operations including user profile retrieval,
post verification (likes, shares, comments), and page following verification.
"""

import logging
from typing import Any, Optional

from src.social_media.enums.platform_enums import Platform
from src.social_media.services.platform_clients.base_client import BaseClient, PlatformAPIError

logger = logging.getLogger(__name__)


class FacebookClient(BaseClient):
    """
    Facebook Graph API client.

    Provides methods for interacting with Facebook Graph API including
    user profiles, likes, follows, shares, and comments verification.
    """

    def __init__(self, access_token: str) -> None:
        """
        Initialize Facebook client.

        Args:
            access_token: Facebook OAuth access token
        """
        super().__init__(Platform.FACEBOOK, access_token)
        logger.info("Facebook client initialized")

    async def get_user_profile(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get Facebook user profile information.

        Args:
            user_id: Facebook user ID (uses "me" for authenticated user if None)

        Returns:
            Dictionary containing user profile data (id, name, email, etc.)

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = FacebookClient("access_token")
            >>> profile = await client.get_user_profile()
            >>> "id" in profile
            True
        """
        try:
            user = user_id or "me"
            fields = "id,name,email,picture,first_name,last_name"

            response = await self.get(
                f"/{user}",
                params={"fields": fields},
            )

            logger.info(
                "Facebook user profile retrieved",
                extra={
                    "user_id": response.get("id"),
                    "name": response.get("name"),
                },
            )

            return response

        except Exception as exc:
            logger.error(
                "Failed to get Facebook user profile",
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
        Verify that authenticated user owns the specified Facebook account.

        Args:
            account_id: Facebook account ID to verify

        Returns:
            True if authenticated user's ID matches account_id

        Example:
            >>> client = FacebookClient("access_token")
            >>> is_owner = await client.verify_account_ownership("123456789")
            >>> isinstance(is_owner, bool)
            True
        """
        try:
            profile = await self.get_user_profile()
            user_id = profile.get("id")

            is_owner = user_id == account_id

            logger.info(
                "Facebook account ownership verification",
                extra={
                    "account_id": account_id,
                    "user_id": user_id,
                    "is_owner": is_owner,
                },
            )

            return is_owner

        except Exception as exc:
            logger.error(
                "Failed to verify Facebook account ownership",
                extra={
                    "account_id": account_id,
                    "error": str(exc),
                },
            )
            return False

    async def verify_like(self, post_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has liked a specific post.

        Args:
            post_id: Facebook post ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has liked the post

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = FacebookClient("access_token")
            >>> has_liked = await client.verify_like("post123")
            >>> isinstance(has_liked, bool)
            True
        """
        try:
            user = user_id or "me"

            response = await self.get(
                f"/{post_id}/likes/{user}",
            )

            has_liked = "data" in response and len(response.get("data", [])) > 0

            logger.info(
                "Facebook like verification",
                extra={
                    "post_id": post_id,
                    "user_id": user,
                    "has_liked": has_liked,
                },
            )

            return has_liked

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Post not liked by user",
                    extra={"post_id": post_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Facebook like",
                extra={
                    "post_id": post_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_follow(self, page_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user follows a specific Facebook page.

        Args:
            page_id: Facebook page ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user follows the page

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = FacebookClient("access_token")
            >>> is_following = await client.verify_follow("page123")
            >>> isinstance(is_following, bool)
            True
        """
        try:
            user = user_id or "me"

            response = await self.get(
                f"/{user}/likes/{page_id}",
            )

            is_following = "data" in response and len(response.get("data", [])) > 0

            logger.info(
                "Facebook follow verification",
                extra={
                    "page_id": page_id,
                    "user_id": user,
                    "is_following": is_following,
                },
            )

            return is_following

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Page not followed by user",
                    extra={"page_id": page_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Facebook follow",
                extra={
                    "page_id": page_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_share(self, post_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has shared a specific post.

        Args:
            post_id: Facebook post ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has shared the post

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = FacebookClient("access_token")
            >>> has_shared = await client.verify_share("post123")
            >>> isinstance(has_shared, bool)
            True
        """
        try:
            user = user_id or "me"

            response = await self.get(
                f"/{post_id}/sharedposts",
                params={"fields": "from"},
            )

            shares = response.get("data", [])
            has_shared = any(share.get("from", {}).get("id") == user for share in shares)

            logger.info(
                "Facebook share verification",
                extra={
                    "post_id": post_id,
                    "user_id": user,
                    "has_shared": has_shared,
                },
            )

            return has_shared

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Post not shared by user",
                    extra={"post_id": post_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Facebook share",
                extra={
                    "post_id": post_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_comment(self, post_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has commented on a specific post.

        Args:
            post_id: Facebook post ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has commented on the post

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = FacebookClient("access_token")
            >>> has_commented = await client.verify_comment("post123")
            >>> isinstance(has_commented, bool)
            True
        """
        try:
            user = user_id or "me"

            response = await self.get(
                f"/{post_id}/comments",
                params={"fields": "from", "limit": 100},
            )

            comments = response.get("data", [])
            has_commented = any(
                comment.get("from", {}).get("id") == user for comment in comments
            )

            logger.info(
                "Facebook comment verification",
                extra={
                    "post_id": post_id,
                    "user_id": user,
                    "has_commented": has_commented,
                },
            )

            return has_commented

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "No comment from user on post",
                    extra={"post_id": post_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Facebook comment",
                extra={
                    "post_id": post_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise
