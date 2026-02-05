"""
Twitter API v2 client.

This module implements Twitter-specific API operations including user profile retrieval,
tweet verification (likes, retweets, replies), and following verification.
"""

import logging
from typing import Any, Optional

from src.social_media.enums.platform_enums import Platform
from src.social_media.services.platform_clients.base_client import BaseClient, PlatformAPIError

logger = logging.getLogger(__name__)


class TwitterClient(BaseClient):
    """
    Twitter API v2 client.

    Provides methods for interacting with Twitter API v2 including
    user profiles, likes, follows, retweets, and replies verification.
    """

    def __init__(self, access_token: str) -> None:
        """
        Initialize Twitter client.

        Args:
            access_token: Twitter OAuth 2.0 access token
        """
        super().__init__(Platform.TWITTER, access_token)
        logger.info("Twitter client initialized")

    async def get_user_profile(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get Twitter user profile information.

        Args:
            user_id: Twitter user ID (uses "me" for authenticated user if None)

        Returns:
            Dictionary containing user profile data (id, name, username, etc.)

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = TwitterClient("access_token")
            >>> profile = await client.get_user_profile()
            >>> "id" in profile["data"]
            True
        """
        try:
            user = user_id or "me"
            fields = "id,name,username,description,profile_image_url,public_metrics,verified"

            response = await self.get(
                f"/users/{user}",
                params={"user.fields": fields},
            )

            user_data = response.get("data", {})

            logger.info(
                "Twitter user profile retrieved",
                extra={
                    "user_id": user_data.get("id"),
                    "username": user_data.get("username"),
                },
            )

            return response

        except Exception as exc:
            logger.error(
                "Failed to get Twitter user profile",
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
        Verify that authenticated user owns the specified Twitter account.

        Args:
            account_id: Twitter account ID to verify

        Returns:
            True if authenticated user's ID matches account_id

        Example:
            >>> client = TwitterClient("access_token")
            >>> is_owner = await client.verify_account_ownership("123456789")
            >>> isinstance(is_owner, bool)
            True
        """
        try:
            profile = await self.get_user_profile()
            user_id = profile.get("data", {}).get("id")

            is_owner = user_id == account_id

            logger.info(
                "Twitter account ownership verification",
                extra={
                    "account_id": account_id,
                    "user_id": user_id,
                    "is_owner": is_owner,
                },
            )

            return is_owner

        except Exception as exc:
            logger.error(
                "Failed to verify Twitter account ownership",
                extra={
                    "account_id": account_id,
                    "error": str(exc),
                },
            )
            return False

    async def verify_like(self, tweet_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has liked a specific tweet.

        Args:
            tweet_id: Twitter tweet ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has liked the tweet

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = TwitterClient("access_token")
            >>> has_liked = await client.verify_like("tweet123")
            >>> isinstance(has_liked, bool)
            True
        """
        try:
            if not user_id:
                profile = await self.get_user_profile()
                user_id = profile.get("data", {}).get("id")

            response = await self.get(
                f"/users/{user_id}/liked_tweets",
                params={"max_results": 100},
            )

            tweets = response.get("data", [])
            has_liked = any(tweet.get("id") == tweet_id for tweet in tweets)

            logger.info(
                "Twitter like verification",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "has_liked": has_liked,
                },
            )

            return has_liked

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Tweet not liked by user",
                    extra={"tweet_id": tweet_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Twitter like",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_follow(self, target_user_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user follows another Twitter account.

        Args:
            target_user_id: Twitter user ID to check if followed
            user_id: User ID doing the following (uses authenticated user if None)

        Returns:
            True if user follows the target account

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = TwitterClient("access_token")
            >>> is_following = await client.verify_follow("user123")
            >>> isinstance(is_following, bool)
            True
        """
        try:
            if not user_id:
                profile = await self.get_user_profile()
                user_id = profile.get("data", {}).get("id")

            response = await self.get(
                f"/users/{user_id}/following",
                params={"max_results": 1000},
            )

            following = response.get("data", [])
            is_following = any(user.get("id") == target_user_id for user in following)

            logger.info(
                "Twitter follow verification",
                extra={
                    "target_user_id": target_user_id,
                    "user_id": user_id,
                    "is_following": is_following,
                },
            )

            return is_following

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "User not following target",
                    extra={"target_user_id": target_user_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Twitter follow",
                extra={
                    "target_user_id": target_user_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_retweet(self, tweet_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has retweeted a specific tweet.

        Args:
            tweet_id: Twitter tweet ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has retweeted the tweet

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = TwitterClient("access_token")
            >>> has_retweeted = await client.verify_retweet("tweet123")
            >>> isinstance(has_retweeted, bool)
            True
        """
        try:
            response = await self.get(
                f"/tweets/{tweet_id}/retweeted_by",
                params={"max_results": 100},
            )

            retweeters = response.get("data", [])

            if not user_id:
                profile = await self.get_user_profile()
                user_id = profile.get("data", {}).get("id")

            has_retweeted = any(user.get("id") == user_id for user in retweeters)

            logger.info(
                "Twitter retweet verification",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "has_retweeted": has_retweeted,
                },
            )

            return has_retweeted

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "Tweet not retweeted by user",
                    extra={"tweet_id": tweet_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Twitter retweet",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise

    async def verify_reply(self, tweet_id: str, user_id: Optional[str] = None) -> bool:
        """
        Verify that user has replied to a specific tweet.

        Args:
            tweet_id: Twitter tweet ID
            user_id: User ID to check (uses authenticated user if None)

        Returns:
            True if user has replied to the tweet

        Raises:
            PlatformAPIError: If API request fails

        Example:
            >>> client = TwitterClient("access_token")
            >>> has_replied = await client.verify_reply("tweet123")
            >>> isinstance(has_replied, bool)
            True
        """
        try:
            if not user_id:
                profile = await self.get_user_profile()
                user_id = profile.get("data", {}).get("id")

            response = await self.get(
                f"/tweets/search/recent",
                params={
                    "query": f"conversation_id:{tweet_id} from:{user_id}",
                    "max_results": 10,
                },
            )

            replies = response.get("data", [])
            has_replied = len(replies) > 0

            logger.info(
                "Twitter reply verification",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "has_replied": has_replied,
                },
            )

            return has_replied

        except PlatformAPIError as exc:
            if exc.status_code == 404:
                logger.info(
                    "No reply from user to tweet",
                    extra={"tweet_id": tweet_id, "user_id": user_id or "me"},
                )
                return False
            logger.error(
                "Failed to verify Twitter reply",
                extra={
                    "tweet_id": tweet_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
            raise
