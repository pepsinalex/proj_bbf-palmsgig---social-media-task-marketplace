"""
JWT service for token generation, validation, and management.

Provides comprehensive JWT functionality including access token generation,
refresh token management, token validation, blacklisting, and secure token rotation.
Implements security best practices and Redis-based token blacklisting.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from jose import JWTError, jwt

from src.shared.config import Settings

logger = logging.getLogger(__name__)


class JWTService:
    """
    JWT service for token operations.

    Handles JWT token generation, validation, refresh, and blacklisting using
    Redis for distributed token revocation and rate limiting.
    """

    def __init__(self, settings: Settings, redis_client: aioredis.Redis) -> None:
        """
        Initialize JWT service.

        Args:
            settings: Application settings instance
            redis_client: Redis client for token blacklisting
        """
        self.settings = settings
        self.redis = redis_client
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

        logger.info(
            "JWT service initialized",
            extra={
                "algorithm": self.algorithm,
                "access_token_expire_minutes": self.access_token_expire_minutes,
                "refresh_token_expire_days": self.refresh_token_expire_days,
            },
        )

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create JWT access token.

        Generates a signed JWT access token with user ID and optional additional claims.
        Sets appropriate expiration time based on configuration.

        Args:
            user_id: User identifier to encode in token
            additional_claims: Optional additional claims to include in token payload

        Returns:
            Encoded JWT access token string

        Raises:
            ValueError: If user_id is empty or invalid
            JWTError: If token encoding fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> token = service.create_access_token("user-123", {"role": "admin"})
        """
        if not user_id:
            logger.error("Cannot create access token with empty user_id")
            raise ValueError("user_id cannot be empty")

        try:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)
            expire = datetime.utcnow() + expires_delta

            to_encode = {
                "sub": user_id,
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
                "jti": secrets.token_urlsafe(32),
            }

            if additional_claims:
                to_encode.update(additional_claims)

            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

            logger.info(
                "Access token created",
                extra={
                    "user_id": user_id,
                    "expires_at": expire.isoformat(),
                    "jti": to_encode["jti"],
                },
            )

            return encoded_jwt

        except Exception as e:
            logger.error(
                "Failed to create access token",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def create_refresh_token(
        self,
        user_id: str,
        token_family: str | None = None,
    ) -> str:
        """
        Create JWT refresh token.

        Generates a signed JWT refresh token with extended expiration time.
        Supports token families for secure token rotation.

        Args:
            user_id: User identifier to encode in token
            token_family: Optional token family ID for rotation tracking

        Returns:
            Encoded JWT refresh token string

        Raises:
            ValueError: If user_id is empty or invalid
            JWTError: If token encoding fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> token = service.create_refresh_token("user-123", "family-abc")
        """
        if not user_id:
            logger.error("Cannot create refresh token with empty user_id")
            raise ValueError("user_id cannot be empty")

        try:
            expires_delta = timedelta(days=self.refresh_token_expire_days)
            expire = datetime.utcnow() + expires_delta

            family = token_family or secrets.token_urlsafe(16)

            to_encode = {
                "sub": user_id,
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
                "jti": secrets.token_urlsafe(32),
                "family": family,
            }

            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

            logger.info(
                "Refresh token created",
                extra={
                    "user_id": user_id,
                    "expires_at": expire.isoformat(),
                    "jti": to_encode["jti"],
                    "family": family,
                },
            )

            return encoded_jwt

        except Exception as e:
            logger.error(
                "Failed to create refresh token",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def decode_token(self, token: str) -> dict[str, Any]:
        """
        Decode and validate JWT token.

        Verifies token signature, expiration, and format. Returns decoded payload
        if valid, raises exception otherwise.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded token payload as dictionary

        Raises:
            JWTError: If token is invalid, expired, or malformed
            ValueError: If token is empty

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> payload = service.decode_token(token)
            >>> user_id = payload["sub"]
        """
        if not token:
            logger.error("Cannot decode empty token")
            raise ValueError("token cannot be empty")

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            logger.debug(
                "Token decoded successfully",
                extra={
                    "user_id": payload.get("sub"),
                    "token_type": payload.get("type"),
                    "jti": payload.get("jti"),
                },
            )

            return payload

        except JWTError as e:
            logger.warning(
                "Token decode failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def validate_access_token(self, token: str) -> dict[str, Any]:
        """
        Validate JWT access token.

        Verifies token is valid, not expired, not blacklisted, and is of type 'access'.
        Returns decoded payload if all checks pass.

        Args:
            token: JWT access token string to validate

        Returns:
            Decoded token payload if valid

        Raises:
            JWTError: If token is invalid or expired
            ValueError: If token is blacklisted or not an access token

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> payload = await service.validate_access_token(token)
        """
        try:
            payload = self.decode_token(token)

            if payload.get("type") != "access":
                logger.warning(
                    "Token validation failed: wrong token type",
                    extra={
                        "expected_type": "access",
                        "actual_type": payload.get("type"),
                        "jti": payload.get("jti"),
                    },
                )
                raise ValueError("Token is not an access token")

            jti = payload.get("jti")
            if jti and await self.is_token_blacklisted(jti):
                logger.warning(
                    "Token validation failed: token is blacklisted",
                    extra={
                        "jti": jti,
                        "user_id": payload.get("sub"),
                    },
                )
                raise ValueError("Token has been revoked")

            logger.debug(
                "Access token validated successfully",
                extra={
                    "user_id": payload.get("sub"),
                    "jti": jti,
                },
            )

            return payload

        except JWTError as e:
            logger.warning(
                "Access token validation failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        except ValueError as e:
            logger.warning(
                "Access token validation failed",
                extra={
                    "error": str(e),
                },
            )
            raise

    async def validate_refresh_token(self, token: str) -> dict[str, Any]:
        """
        Validate JWT refresh token.

        Verifies token is valid, not expired, not blacklisted, and is of type 'refresh'.
        Returns decoded payload if all checks pass.

        Args:
            token: JWT refresh token string to validate

        Returns:
            Decoded token payload if valid

        Raises:
            JWTError: If token is invalid or expired
            ValueError: If token is blacklisted or not a refresh token

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> payload = await service.validate_refresh_token(token)
        """
        try:
            payload = self.decode_token(token)

            if payload.get("type") != "refresh":
                logger.warning(
                    "Token validation failed: wrong token type",
                    extra={
                        "expected_type": "refresh",
                        "actual_type": payload.get("type"),
                        "jti": payload.get("jti"),
                    },
                )
                raise ValueError("Token is not a refresh token")

            jti = payload.get("jti")
            if jti and await self.is_token_blacklisted(jti):
                logger.warning(
                    "Token validation failed: token is blacklisted",
                    extra={
                        "jti": jti,
                        "user_id": payload.get("sub"),
                    },
                )
                raise ValueError("Token has been revoked")

            logger.debug(
                "Refresh token validated successfully",
                extra={
                    "user_id": payload.get("sub"),
                    "jti": jti,
                    "family": payload.get("family"),
                },
            )

            return payload

        except JWTError as e:
            logger.warning(
                "Refresh token validation failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        except ValueError as e:
            logger.warning(
                "Refresh token validation failed",
                extra={
                    "error": str(e),
                },
            )
            raise

    async def blacklist_token(self, jti: str, expires_in_seconds: int) -> None:
        """
        Add token to blacklist.

        Stores token JTI in Redis with expiration matching the token's remaining lifetime.
        Used for token revocation and logout functionality.

        Args:
            jti: Token JTI (JWT ID) to blacklist
            expires_in_seconds: Time until token naturally expires

        Raises:
            ValueError: If jti is empty or expires_in_seconds is invalid
            Exception: If Redis operation fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> await service.blacklist_token("token-jti-123", 1800)
        """
        if not jti:
            logger.error("Cannot blacklist token with empty jti")
            raise ValueError("jti cannot be empty")

        if expires_in_seconds <= 0:
            logger.warning(
                "Token expiration is non-positive, not blacklisting",
                extra={
                    "jti": jti,
                    "expires_in_seconds": expires_in_seconds,
                },
            )
            return

        try:
            blacklist_key = f"token:blacklist:{jti}"
            await self.redis.setex(blacklist_key, expires_in_seconds, "1")

            logger.info(
                "Token blacklisted",
                extra={
                    "jti": jti,
                    "expires_in_seconds": expires_in_seconds,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to blacklist token",
                extra={
                    "jti": jti,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted.

        Queries Redis to determine if a token has been revoked.

        Args:
            jti: Token JTI to check

        Returns:
            True if token is blacklisted, False otherwise

        Raises:
            Exception: If Redis operation fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> is_blacklisted = await service.is_token_blacklisted("token-jti-123")
        """
        if not jti:
            return False

        try:
            blacklist_key = f"token:blacklist:{jti}"
            result = await self.redis.exists(blacklist_key)
            is_blacklisted = result > 0

            if is_blacklisted:
                logger.debug(
                    "Token is blacklisted",
                    extra={"jti": jti},
                )

            return is_blacklisted

        except Exception as e:
            logger.error(
                "Failed to check token blacklist status",
                extra={
                    "jti": jti,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def blacklist_family(self, family: str, expires_in_seconds: int) -> None:
        """
        Blacklist all tokens in a token family.

        Used to revoke all refresh tokens in a family when token theft is detected
        or user explicitly logs out from all devices.

        Args:
            family: Token family identifier
            expires_in_seconds: Time until tokens naturally expire

        Raises:
            ValueError: If family is empty or expires_in_seconds is invalid
            Exception: If Redis operation fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> await service.blacklist_family("family-abc", 86400)
        """
        if not family:
            logger.error("Cannot blacklist family with empty family ID")
            raise ValueError("family cannot be empty")

        if expires_in_seconds <= 0:
            logger.warning(
                "Family expiration is non-positive, not blacklisting",
                extra={
                    "family": family,
                    "expires_in_seconds": expires_in_seconds,
                },
            )
            return

        try:
            family_key = f"token:family:blacklist:{family}"
            await self.redis.setex(family_key, expires_in_seconds, "1")

            logger.info(
                "Token family blacklisted",
                extra={
                    "family": family,
                    "expires_in_seconds": expires_in_seconds,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to blacklist token family",
                extra={
                    "family": family,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def is_family_blacklisted(self, family: str) -> bool:
        """
        Check if token family is blacklisted.

        Args:
            family: Token family identifier to check

        Returns:
            True if family is blacklisted, False otherwise

        Raises:
            Exception: If Redis operation fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> is_blacklisted = await service.is_family_blacklisted("family-abc")
        """
        if not family:
            return False

        try:
            family_key = f"token:family:blacklist:{family}"
            result = await self.redis.exists(family_key)
            is_blacklisted = result > 0

            if is_blacklisted:
                logger.debug(
                    "Token family is blacklisted",
                    extra={"family": family},
                )

            return is_blacklisted

        except Exception as e:
            logger.error(
                "Failed to check family blacklist status",
                extra={
                    "family": family,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> tuple[str, str]:
        """
        Refresh access and refresh tokens.

        Validates the provided refresh token and generates a new access token and
        refresh token pair. Implements secure token rotation by blacklisting the
        old refresh token.

        Args:
            refresh_token: Current refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            JWTError: If refresh token is invalid or expired
            ValueError: If refresh token is blacklisted or invalid
            Exception: If token generation or blacklisting fails

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> access_token, refresh_token = await service.refresh_tokens(old_refresh_token)
        """
        try:
            payload = await self.validate_refresh_token(refresh_token)

            user_id = payload.get("sub")
            if not user_id:
                logger.error("Refresh token missing user ID")
                raise ValueError("Invalid token: missing user ID")

            family = payload.get("family")
            if family and await self.is_family_blacklisted(family):
                logger.warning(
                    "Token refresh failed: family is blacklisted",
                    extra={
                        "family": family,
                        "user_id": user_id,
                    },
                )
                raise ValueError("Token family has been revoked")

            new_access_token = self.create_access_token(user_id)
            new_refresh_token = self.create_refresh_token(user_id, token_family=family)

            old_jti = payload.get("jti")
            if old_jti:
                exp = payload.get("exp")
                if exp:
                    expires_in = int(exp - datetime.utcnow().timestamp())
                    if expires_in > 0:
                        await self.blacklist_token(old_jti, expires_in)

            logger.info(
                "Tokens refreshed successfully",
                extra={
                    "user_id": user_id,
                    "family": family,
                    "old_jti": old_jti,
                },
            )

            return new_access_token, new_refresh_token

        except (JWTError, ValueError) as e:
            logger.warning(
                "Token refresh failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        except Exception as e:
            logger.error(
                "Token refresh failed with unexpected error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def get_token_expiry(self, token: str) -> datetime | None:
        """
        Get token expiration timestamp.

        Args:
            token: JWT token string

        Returns:
            Token expiration datetime, or None if token is invalid

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> expiry = service.get_token_expiry(token)
        """
        try:
            payload = self.decode_token(token)
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp)
            return None
        except Exception as e:
            logger.warning(
                "Failed to get token expiry",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None

    def get_token_remaining_seconds(self, token: str) -> int:
        """
        Get remaining seconds until token expires.

        Args:
            token: JWT token string

        Returns:
            Remaining seconds until expiration, or 0 if expired or invalid

        Example:
            >>> service = JWTService(settings, redis_client)
            >>> remaining = service.get_token_remaining_seconds(token)
        """
        try:
            expiry = self.get_token_expiry(token)
            if expiry:
                remaining = int((expiry - datetime.utcnow()).total_seconds())
                return max(0, remaining)
            return 0
        except Exception as e:
            logger.warning(
                "Failed to get token remaining seconds",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0
