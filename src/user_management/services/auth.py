"""
Authentication service for user login, logout, and token refresh.

Provides comprehensive authentication functionality including login with device
fingerprinting, logout with session termination, token refresh with rotation,
and security features like account locking.
"""

import logging
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import Settings
from src.shared.models.user import User
from src.user_management.services.jwt import JWTService
from src.user_management.services.password import PasswordService
from src.user_management.services.session import SessionService

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service.

    Handles user authentication operations including login, logout, token refresh,
    and session management with security features.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: aioredis.Redis,
        settings: Settings,
    ) -> None:
        """
        Initialize authentication service.

        Args:
            db_session: Database session for persistence operations
            redis_client: Redis client for token blacklisting
            settings: Application settings instance
        """
        self.db = db_session
        self.redis = redis_client
        self.settings = settings
        self.jwt_service = JWTService(settings, redis_client)
        self.session_service = SessionService(db_session)
        self.password_service = PasswordService()

        logger.info("Authentication service initialized")

    async def login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, str | dict]:
        """
        Authenticate user and create session.

        Validates credentials, creates JWT tokens, and establishes a new session
        with device fingerprinting.

        Args:
            email: User email address
            password: Plain text password
            user_agent: Browser user agent string
            ip_address: Client IP address

        Returns:
            Dictionary containing access_token, refresh_token, token_type, and user info

        Raises:
            ValueError: If credentials are invalid or account is locked
            Exception: If authentication process fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.login(
            ...     email="user@example.com",
            ...     password="SecurePass123",
            ...     user_agent="Mozilla/5.0...",
            ...     ip_address="192.168.1.1"
            ... )
        """
        if not email or not password:
            logger.warning(
                "Login attempt with empty credentials",
                extra={"has_email": bool(email), "has_password": bool(password)},
            )
            raise ValueError("Email and password are required")

        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    "Login failed: user not found",
                    extra={"email": email, "ip_address": ip_address},
                )
                raise ValueError("Invalid email or password")

            if user.is_locked:
                logger.warning(
                    "Login failed: account is locked",
                    extra={
                        "user_id": user.id,
                        "email": email,
                        "locked_until": user.locked_until.isoformat()
                        if user.locked_until
                        else None,
                    },
                )
                raise ValueError(
                    f"Account is locked until {user.locked_until.isoformat()}"
                    if user.locked_until
                    else "Account is locked"
                )

            if not user.is_active:
                logger.warning(
                    "Login failed: account is inactive",
                    extra={"user_id": user.id, "email": email},
                )
                raise ValueError("Account is inactive")

            if not self.password_service.verify_password(password, user.password_hash):
                user.increment_failed_login()
                await self.db.commit()

                logger.warning(
                    "Login failed: invalid password",
                    extra={
                        "user_id": user.id,
                        "email": email,
                        "failed_attempts": user.failed_login_attempts,
                        "ip_address": ip_address,
                    },
                )
                raise ValueError("Invalid email or password")

            user.reset_failed_login()

            # Check if MFA is enabled for the user
            if user.mfa_enabled:
                # Store pending MFA session in Redis (5 minutes)
                pending_key = f"mfa:pending:{user.id}"
                import json

                pending_data = {
                    "user_id": user.id,
                    "email": user.email,
                    "user_agent": user_agent,
                    "ip_address": ip_address,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await self.redis.setex(pending_key, 300, json.dumps(pending_data))

                logger.info(
                    "MFA challenge required for user",
                    extra={"user_id": user.id, "email": user.email},
                )

                return {
                    "mfa_required": True,
                    "mfa_token": user.id,  # Temporary identifier for MFA flow
                    "message": "MFA verification required",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                    },
                }

            # No MFA - proceed with normal login
            user.update_last_login(ip_address)
            await self.db.commit()

            access_token = self.jwt_service.create_access_token(
                user_id=user.id,
                additional_claims={
                    "email": user.email,
                    "is_verified": user.is_verified,
                },
            )

            refresh_token = self.jwt_service.create_refresh_token(user_id=user.id)

            refresh_payload = self.jwt_service.decode_token(refresh_token)
            refresh_jti = refresh_payload.get("jti")

            expires_at = datetime.utcnow() + timedelta(
                days=self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )

            session = await self.session_service.create_session(
                user_id=user.id,
                refresh_token_jti=refresh_jti,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=expires_at,
            )

            logger.info(
                "User logged in successfully",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "session_id": session.id,
                    "ip_address": ip_address,
                },
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_verified": user.is_verified,
                },
            }

        except ValueError as e:
            logger.warning(
                "Login failed: validation error",
                extra={"email": email, "error": str(e)},
            )
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Login failed with unexpected error",
                extra={
                    "email": email,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def logout(
        self,
        access_token: str,
        refresh_token: str | None = None,
    ) -> dict[str, str]:
        """
        Logout user and terminate session.

        Blacklists the access token and optionally the refresh token, and
        terminates the associated session.

        Args:
            access_token: Current access token
            refresh_token: Optional refresh token to blacklist

        Returns:
            Dictionary with success message

        Raises:
            ValueError: If token is invalid
            Exception: If logout process fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.logout(access_token, refresh_token)
        """
        try:
            access_payload = await self.jwt_service.validate_access_token(access_token)

            user_id = access_payload.get("sub")
            access_jti = access_payload.get("jti")

            if access_jti:
                remaining_seconds = self.jwt_service.get_token_remaining_seconds(
                    access_token
                )
                if remaining_seconds > 0:
                    await self.jwt_service.blacklist_token(access_jti, remaining_seconds)

            session_terminated = False
            if refresh_token:
                try:
                    refresh_payload = await self.jwt_service.validate_refresh_token(
                        refresh_token
                    )
                    refresh_jti = refresh_payload.get("jti")

                    if refresh_jti:
                        remaining_seconds = self.jwt_service.get_token_remaining_seconds(
                            refresh_token
                        )
                        if remaining_seconds > 0:
                            await self.jwt_service.blacklist_token(
                                refresh_jti, remaining_seconds
                            )

                        session = await self.session_service.get_session_by_jti(
                            refresh_jti
                        )
                        if session:
                            await self.session_service.terminate_session(session.id)
                            session_terminated = True

                except Exception as e:
                    logger.warning(
                        "Failed to process refresh token during logout",
                        extra={
                            "user_id": user_id,
                            "error": str(e),
                        },
                    )

            logger.info(
                "User logged out successfully",
                extra={
                    "user_id": user_id,
                    "session_terminated": session_terminated,
                },
            )

            return {
                "message": "Logged out successfully",
                "session_terminated": session_terminated,
            }

        except ValueError as e:
            logger.warning(
                "Logout failed: validation error",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Logout failed with unexpected error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def logout_all_devices(
        self,
        user_id: str,
        current_session_id: str | None = None,
    ) -> dict[str, int]:
        """
        Logout user from all devices.

        Terminates all user sessions except optionally the current one.

        Args:
            user_id: User identifier
            current_session_id: Optional current session ID to preserve

        Returns:
            Dictionary with count of terminated sessions

        Raises:
            Exception: If logout process fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.logout_all_devices("user-123")
        """
        try:
            sessions = await self.session_service.get_user_sessions(
                user_id, active_only=True
            )

            count = 0
            for session in sessions:
                if current_session_id and session.id == current_session_id:
                    continue

                await self.session_service.terminate_session(session.id)

                remaining_seconds = self.jwt_service.get_token_remaining_seconds(
                    session.refresh_token_jti
                )
                if remaining_seconds > 0:
                    await self.jwt_service.blacklist_token(
                        session.refresh_token_jti, remaining_seconds
                    )

                count += 1

            logger.info(
                "User logged out from all devices",
                extra={
                    "user_id": user_id,
                    "sessions_terminated": count,
                    "current_session_preserved": bool(current_session_id),
                },
            )

            return {
                "sessions_terminated": count,
            }

        except Exception as e:
            logger.error(
                "Logout all devices failed",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, str | int]:
        """
        Refresh access and refresh tokens.

        Validates the refresh token, generates new token pair with rotation,
        and updates the session.

        Args:
            refresh_token: Current refresh token
            user_agent: Browser user agent string
            ip_address: Client IP address

        Returns:
            Dictionary containing new access_token, refresh_token, and token_type

        Raises:
            ValueError: If refresh token is invalid or expired
            Exception: If token refresh fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.refresh_tokens(
            ...     refresh_token=old_refresh_token,
            ...     user_agent="Mozilla/5.0...",
            ...     ip_address="192.168.1.1"
            ... )
        """
        try:
            old_payload = await self.jwt_service.validate_refresh_token(refresh_token)

            user_id = old_payload.get("sub")
            old_jti = old_payload.get("jti")

            if not user_id:
                logger.error("Refresh token missing user ID")
                raise ValueError("Invalid refresh token: missing user ID")

            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    "Token refresh failed: user not found",
                    extra={"user_id": user_id},
                )
                raise ValueError("User not found")

            if not user.is_active:
                logger.warning(
                    "Token refresh failed: user is inactive",
                    extra={"user_id": user_id},
                )
                raise ValueError("User account is inactive")

            session = await self.session_service.get_session_by_jti(old_jti)
            if not session:
                logger.warning(
                    "Token refresh failed: session not found",
                    extra={"user_id": user_id, "jti": old_jti},
                )
                raise ValueError("Session not found")

            if not session.is_valid:
                logger.warning(
                    "Token refresh failed: session is invalid",
                    extra={
                        "user_id": user_id,
                        "session_id": session.id,
                        "is_active": session.is_active,
                        "is_expired": session.is_expired,
                    },
                )
                raise ValueError("Session is no longer valid")

            new_access_token, new_refresh_token = await self.jwt_service.refresh_tokens(
                refresh_token
            )

            new_refresh_payload = self.jwt_service.decode_token(new_refresh_token)
            new_jti = new_refresh_payload.get("jti")

            session.refresh_token_jti = new_jti
            session.update_activity(ip_address)
            await self.db.commit()

            logger.info(
                "Tokens refreshed successfully",
                extra={
                    "user_id": user_id,
                    "session_id": session.id,
                    "old_jti": old_jti,
                    "new_jti": new_jti,
                },
            )

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }

        except ValueError as e:
            logger.warning(
                "Token refresh failed: validation error",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Token refresh failed with unexpected error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def validate_session(
        self,
        access_token: str,
        ip_address: str | None = None,
    ) -> dict[str, str | bool]:
        """
        Validate user session from access token.

        Args:
            access_token: Current access token
            ip_address: Optional IP address for activity tracking

        Returns:
            Dictionary with user_id and session validity

        Raises:
            ValueError: If token is invalid
            Exception: If validation fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.validate_session(access_token)
        """
        try:
            payload = await self.jwt_service.validate_access_token(access_token)

            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token: missing user ID")

            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    "Session validation failed: user not found",
                    extra={"user_id": user_id},
                )
                raise ValueError("User not found")

            if not user.is_active:
                logger.warning(
                    "Session validation failed: user is inactive",
                    extra={"user_id": user_id},
                )
                raise ValueError("User account is inactive")

            logger.debug(
                "Session validated successfully",
                extra={"user_id": user_id},
            )

            return {
                "user_id": user_id,
                "email": user.email,
                "is_verified": user.is_verified,
                "is_valid": True,
            }

        except ValueError as e:
            logger.warning(
                "Session validation failed",
                extra={"error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Session validation failed with unexpected error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_user_sessions(self, user_id: str) -> list[dict]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session information dictionaries

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> sessions = await service.get_user_sessions("user-123")
        """
        try:
            sessions = await self.session_service.get_user_sessions(
                user_id, active_only=True
            )

            result = []
            for session in sessions:
                session_info = await self.session_service.get_session_info(session.id)
                if session_info:
                    result.append(session_info)

            logger.debug(
                "User sessions retrieved",
                extra={"user_id": user_id, "session_count": len(result)},
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get user sessions",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def complete_mfa_login(
        self,
        user_id: str,
        mfa_verified: bool = True,
    ) -> dict[str, str | dict]:
        """
        Complete login after successful MFA verification.

        Creates tokens and session after MFA verification is complete.

        Args:
            user_id: User identifier
            mfa_verified: Whether MFA was successfully verified (default: True)

        Returns:
            Dictionary containing access_token, refresh_token, token_type, and user info

        Raises:
            ValueError: If MFA session not found or expired
            Exception: If login completion fails

        Example:
            >>> service = AuthService(db_session, redis_client, settings)
            >>> result = await service.complete_mfa_login("user-123")
        """
        try:
            if not mfa_verified:
                raise ValueError("MFA verification required")

            # Retrieve pending MFA session from Redis
            pending_key = f"mfa:pending:{user_id}"
            pending_data_json = await self.redis.get(pending_key)

            if not pending_data_json:
                logger.warning(
                    "MFA session not found or expired",
                    extra={"user_id": user_id},
                )
                raise ValueError("MFA session not found or expired. Please login again.")

            import json

            pending_data = json.loads(pending_data_json)
            user_agent = pending_data.get("user_agent")
            ip_address = pending_data.get("ip_address")

            # Get user from database
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    "MFA login completion failed: user not found",
                    extra={"user_id": user_id},
                )
                raise ValueError("User not found")

            if not user.is_active:
                logger.warning(
                    "MFA login completion failed: account is inactive",
                    extra={"user_id": user_id},
                )
                raise ValueError("Account is inactive")

            # Update last login
            user.update_last_login(ip_address)
            await self.db.commit()

            # Create tokens
            access_token = self.jwt_service.create_access_token(
                user_id=user.id,
                additional_claims={
                    "email": user.email,
                    "is_verified": user.is_verified,
                    "mfa_verified": True,
                },
            )

            refresh_token = self.jwt_service.create_refresh_token(user_id=user.id)

            refresh_payload = self.jwt_service.decode_token(refresh_token)
            refresh_jti = refresh_payload.get("jti")

            expires_at = datetime.utcnow() + timedelta(
                days=self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            )

            # Create session
            session = await self.session_service.create_session(
                user_id=user.id,
                refresh_token_jti=refresh_jti,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=expires_at,
            )

            # Clean up pending MFA session
            await self.redis.delete(pending_key)

            logger.info(
                "User logged in successfully after MFA verification",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "session_id": session.id,
                    "ip_address": ip_address,
                },
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_verified": user.is_verified,
                },
            }

        except ValueError as e:
            logger.warning(
                "MFA login completion failed: validation error",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "MFA login completion failed with unexpected error",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
