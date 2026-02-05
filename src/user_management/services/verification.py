"""
Verification Service for email and phone verification workflows.

Handles token generation, Redis storage, and verification logic.
"""

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for managing email and phone verification tokens."""

    def __init__(
        self,
        redis_client: Redis,
        token_expiry_minutes: int = 15,
        token_length: int = 6,
        rate_limit_window_seconds: int = 60,
        max_attempts_per_window: int = 3,
    ):
        """
        Initialize the verification service.

        Args:
            redis_client: Redis client for token storage
            token_expiry_minutes: Token expiration time in minutes (default: 15)
            token_length: Length of verification token (default: 6)
            rate_limit_window_seconds: Rate limit window in seconds (default: 60)
            max_attempts_per_window: Max verification attempts per window (default: 3)
        """
        self.redis = redis_client
        self.token_expiry_minutes = token_expiry_minutes
        self.token_length = token_length
        self.rate_limit_window = rate_limit_window_seconds
        self.max_attempts = max_attempts_per_window
        logger.info(
            f"VerificationService initialized: token_expiry={token_expiry_minutes}m, "
            f"token_length={token_length}, rate_limit={max_attempts_per_window}/"
            f"{rate_limit_window_seconds}s"
        )

    def generate_token(self) -> str:
        """
        Generate a random verification token.

        Returns:
            Random alphanumeric token of configured length
        """
        characters = string.digits + string.ascii_uppercase
        token = "".join(secrets.choice(characters) for _ in range(self.token_length))
        logger.debug(f"Generated verification token of length {self.token_length}")
        return token

    async def store_token(
        self, identifier: str, token: str, token_type: str, user_id: Optional[str] = None
    ) -> bool:
        """
        Store verification token in Redis with expiration.

        Args:
            identifier: Email or phone number
            token: Verification token
            token_type: Type of token ('email' or 'phone')
            user_id: Optional user ID to associate with token

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            key = f"verification:{token_type}:{identifier}"
            value = f"{token}:{user_id or ''}"
            expiry_seconds = self.token_expiry_minutes * 60

            await self.redis.setex(key, expiry_seconds, value)
            logger.info(
                f"Stored {token_type} verification token for {identifier}, "
                f"expires in {self.token_expiry_minutes} minutes"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to store verification token for {identifier}: {e}", exc_info=True
            )
            return False

    async def verify_token(
        self, identifier: str, token: str, token_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verify a token against stored value.

        Args:
            identifier: Email or phone number
            token: Token to verify
            token_type: Type of token ('email' or 'phone')

        Returns:
            Tuple of (is_valid, user_id)
            - is_valid: True if token is valid
            - user_id: User ID if token is valid, None otherwise
        """
        try:
            if not await self.check_rate_limit(identifier, token_type):
                logger.warning(f"Rate limit exceeded for {identifier}")
                return False, None

            key = f"verification:{token_type}:{identifier}"
            stored_value = await self.redis.get(key)

            if not stored_value:
                logger.warning(f"No verification token found for {identifier}")
                await self.increment_attempt(identifier, token_type)
                return False, None

            stored_token, user_id = stored_value.decode("utf-8").split(":", 1)

            if stored_token != token:
                logger.warning(f"Invalid token provided for {identifier}")
                await self.increment_attempt(identifier, token_type)
                return False, None

            await self.redis.delete(key)
            await self.clear_rate_limit(identifier, token_type)
            logger.info(f"Token verified successfully for {identifier}")
            return True, user_id if user_id else None

        except Exception as e:
            logger.error(f"Token verification error for {identifier}: {e}", exc_info=True)
            return False, None

    async def check_rate_limit(self, identifier: str, token_type: str) -> bool:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: Email or phone number
            token_type: Type of verification

        Returns:
            True if within rate limit, False if exceeded
        """
        try:
            key = f"verification:ratelimit:{token_type}:{identifier}"
            attempts = await self.redis.get(key)

            if attempts is None:
                return True

            attempt_count = int(attempts.decode("utf-8"))
            is_within_limit = attempt_count < self.max_attempts

            if not is_within_limit:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: {attempt_count}/{self.max_attempts}"
                )

            return is_within_limit

        except Exception as e:
            logger.error(f"Error checking rate limit for {identifier}: {e}", exc_info=True)
            return True

    async def increment_attempt(self, identifier: str, token_type: str) -> None:
        """
        Increment failed verification attempt counter.

        Args:
            identifier: Email or phone number
            token_type: Type of verification
        """
        try:
            key = f"verification:ratelimit:{token_type}:{identifier}"
            current = await self.redis.get(key)

            if current is None:
                await self.redis.setex(key, self.rate_limit_window, "1")
            else:
                await self.redis.incr(key)

            logger.debug(f"Incremented attempt counter for {identifier}")

        except Exception as e:
            logger.error(
                f"Error incrementing attempt counter for {identifier}: {e}", exc_info=True
            )

    async def clear_rate_limit(self, identifier: str, token_type: str) -> None:
        """
        Clear rate limit counter for identifier.

        Args:
            identifier: Email or phone number
            token_type: Type of verification
        """
        try:
            key = f"verification:ratelimit:{token_type}:{identifier}"
            await self.redis.delete(key)
            logger.debug(f"Cleared rate limit for {identifier}")
        except Exception as e:
            logger.error(f"Error clearing rate limit for {identifier}: {e}", exc_info=True)

    async def get_token_ttl(self, identifier: str, token_type: str) -> Optional[int]:
        """
        Get time-to-live for a verification token.

        Args:
            identifier: Email or phone number
            token_type: Type of token

        Returns:
            TTL in seconds, or None if token doesn't exist
        """
        try:
            key = f"verification:{token_type}:{identifier}"
            ttl = await self.redis.ttl(key)

            if ttl <= 0:
                return None

            logger.debug(f"Token TTL for {identifier}: {ttl} seconds")
            return ttl

        except Exception as e:
            logger.error(f"Error getting token TTL for {identifier}: {e}", exc_info=True)
            return None

    async def resend_token(self, identifier: str, token_type: str) -> Optional[str]:
        """
        Generate and store a new verification token.

        Args:
            identifier: Email or phone number
            token_type: Type of token ('email' or 'phone')

        Returns:
            New token if generated successfully, None otherwise
        """
        try:
            if not await self.check_rate_limit(identifier, f"{token_type}:resend"):
                logger.warning(f"Resend rate limit exceeded for {identifier}")
                return None

            new_token = self.generate_token()
            success = await self.store_token(identifier, new_token, token_type)

            if success:
                await self.increment_attempt(identifier, f"{token_type}:resend")
                logger.info(f"Token resent for {identifier}")
                return new_token

            return None

        except Exception as e:
            logger.error(f"Error resending token for {identifier}: {e}", exc_info=True)
            return None
