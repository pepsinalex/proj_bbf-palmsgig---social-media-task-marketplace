"""
Session management service for tracking user sessions and devices.

Provides session tracking functionality including device fingerprinting,
session creation, validation, and cleanup. Manages user sessions across
multiple devices with proper expiration and security features.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.auth import UserSession

logger = logging.getLogger(__name__)


class SessionService:
    """
    Session management service.

    Handles user session lifecycle including creation, validation, updates,
    and termination. Tracks device information and IP addresses for security.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize session service.

        Args:
            db_session: Database session for persistence operations
        """
        self.db = db_session

        logger.debug("Session service initialized")

    def generate_device_fingerprint(
        self,
        user_agent: str | None,
        ip_address: str | None,
    ) -> str:
        """
        Generate device fingerprint from user agent and IP address.

        Creates a unique identifier for a device based on its user agent and IP address.
        Used for tracking and identifying sessions across requests.

        Args:
            user_agent: Browser user agent string
            ip_address: Client IP address

        Returns:
            Device fingerprint hash string

        Example:
            >>> service = SessionService(db_session)
            >>> fingerprint = service.generate_device_fingerprint(
            ...     "Mozilla/5.0...",
            ...     "192.168.1.1"
            ... )
        """
        components = [
            user_agent or "unknown",
            ip_address or "unknown",
        ]

        fingerprint_data = "|".join(components)
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()

        logger.debug(
            "Device fingerprint generated",
            extra={
                "has_user_agent": bool(user_agent),
                "has_ip": bool(ip_address),
                "fingerprint": fingerprint_hash[:16],
            },
        )

        return fingerprint_hash

    async def create_session(
        self,
        user_id: str,
        refresh_token_jti: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserSession:
        """
        Create a new user session.

        Creates and persists a new session record with device fingerprinting
        and metadata tracking.

        Args:
            user_id: User identifier
            refresh_token_jti: JWT ID of the associated refresh token
            user_agent: Browser user agent string
            ip_address: Client IP address
            expires_at: Session expiration timestamp
            metadata: Additional session metadata

        Returns:
            Created UserSession instance

        Raises:
            ValueError: If required parameters are invalid
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> session = await service.create_session(
            ...     user_id="user-123",
            ...     refresh_token_jti="jti-abc",
            ...     user_agent="Mozilla/5.0...",
            ...     ip_address="192.168.1.1",
            ...     expires_at=datetime.utcnow() + timedelta(days=7)
            ... )
        """
        if not user_id:
            logger.error("Cannot create session with empty user_id")
            raise ValueError("user_id cannot be empty")

        if not refresh_token_jti:
            logger.error("Cannot create session with empty refresh_token_jti")
            raise ValueError("refresh_token_jti cannot be empty")

        try:
            device_fingerprint = self.generate_device_fingerprint(user_agent, ip_address)

            if not expires_at:
                expires_at = datetime.utcnow() + timedelta(days=7)

            session = UserSession(
                user_id=user_id,
                refresh_token_jti=refresh_token_jti,
                device_fingerprint=device_fingerprint,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=expires_at,
                metadata=metadata or {},
                is_active=True,
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            logger.info(
                "Session created",
                extra={
                    "session_id": session.id,
                    "user_id": user_id,
                    "device_fingerprint": device_fingerprint[:16],
                    "expires_at": expires_at.isoformat(),
                },
            )

            return session

        except ValueError as e:
            logger.error(
                "Session creation failed: validation error",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Session creation failed",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_session_by_jti(self, refresh_token_jti: str) -> UserSession | None:
        """
        Get session by refresh token JTI.

        Args:
            refresh_token_jti: JWT ID of the refresh token

        Returns:
            UserSession instance if found, None otherwise

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> session = await service.get_session_by_jti("jti-abc")
        """
        if not refresh_token_jti:
            return None

        try:
            stmt = select(UserSession).where(
                UserSession.refresh_token_jti == refresh_token_jti
            )
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if session:
                logger.debug(
                    "Session found by JTI",
                    extra={
                        "session_id": session.id,
                        "user_id": session.user_id,
                        "jti": refresh_token_jti,
                    },
                )
            else:
                logger.debug(
                    "No session found for JTI",
                    extra={"jti": refresh_token_jti},
                )

            return session

        except Exception as e:
            logger.error(
                "Failed to get session by JTI",
                extra={
                    "jti": refresh_token_jti,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> list[UserSession]:
        """
        Get all sessions for a user.

        Args:
            user_id: User identifier
            active_only: If True, return only active sessions

        Returns:
            List of UserSession instances

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> sessions = await service.get_user_sessions("user-123")
        """
        if not user_id:
            return []

        try:
            stmt = select(UserSession).where(UserSession.user_id == user_id)

            if active_only:
                stmt = stmt.where(UserSession.is_active == True)  # noqa: E712

            stmt = stmt.order_by(UserSession.last_activity_at.desc())

            result = await self.db.execute(stmt)
            sessions = list(result.scalars().all())

            logger.debug(
                "User sessions retrieved",
                extra={
                    "user_id": user_id,
                    "session_count": len(sessions),
                    "active_only": active_only,
                },
            )

            return sessions

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

    async def update_session_activity(
        self,
        session_id: str,
        ip_address: str | None = None,
    ) -> UserSession | None:
        """
        Update session last activity timestamp.

        Args:
            session_id: Session identifier
            ip_address: Optional updated IP address

        Returns:
            Updated UserSession instance if found, None otherwise

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> session = await service.update_session_activity(
            ...     session_id="session-123",
            ...     ip_address="192.168.1.2"
            ... )
        """
        if not session_id:
            return None

        try:
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                logger.debug(
                    "Session not found for activity update",
                    extra={"session_id": session_id},
                )
                return None

            session.last_activity_at = datetime.utcnow()
            if ip_address:
                session.ip_address = ip_address

            await self.db.commit()
            await self.db.refresh(session)

            logger.debug(
                "Session activity updated",
                extra={
                    "session_id": session_id,
                    "user_id": session.user_id,
                },
            )

            return session

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to update session activity",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a user session.

        Marks session as inactive and records termination timestamp.

        Args:
            session_id: Session identifier

        Returns:
            True if session was terminated, False if not found

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> success = await service.terminate_session("session-123")
        """
        if not session_id:
            return False

        try:
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                logger.debug(
                    "Session not found for termination",
                    extra={"session_id": session_id},
                )
                return False

            session.is_active = False
            session.terminated_at = datetime.utcnow()

            await self.db.commit()

            logger.info(
                "Session terminated",
                extra={
                    "session_id": session_id,
                    "user_id": session.user_id,
                },
            )

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to terminate session",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def terminate_user_sessions(
        self,
        user_id: str,
        exclude_session_id: str | None = None,
    ) -> int:
        """
        Terminate all sessions for a user.

        Optionally excludes a specific session (e.g., current session).

        Args:
            user_id: User identifier
            exclude_session_id: Session ID to exclude from termination

        Returns:
            Number of sessions terminated

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> count = await service.terminate_user_sessions(
            ...     user_id="user-123",
            ...     exclude_session_id="session-current"
            ... )
        """
        if not user_id:
            return 0

        try:
            stmt = select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,  # noqa: E712
            )

            if exclude_session_id:
                stmt = stmt.where(UserSession.id != exclude_session_id)

            result = await self.db.execute(stmt)
            sessions = list(result.scalars().all())

            count = 0
            for session in sessions:
                session.is_active = False
                session.terminated_at = datetime.utcnow()
                count += 1

            await self.db.commit()

            logger.info(
                "User sessions terminated",
                extra={
                    "user_id": user_id,
                    "sessions_terminated": count,
                    "excluded_session": exclude_session_id,
                },
            )

            return count

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to terminate user sessions",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Deactivates all sessions that have passed their expiration time.

        Returns:
            Number of sessions cleaned up

        Raises:
            Exception: If database operation fails

        Example:
            >>> service = SessionService(db_session)
            >>> count = await service.cleanup_expired_sessions()
        """
        try:
            now = datetime.utcnow()

            stmt = select(UserSession).where(
                UserSession.expires_at < now,
                UserSession.is_active == True,  # noqa: E712
            )

            result = await self.db.execute(stmt)
            sessions = list(result.scalars().all())

            count = 0
            for session in sessions:
                session.is_active = False
                session.terminated_at = now
                count += 1

            await self.db.commit()

            logger.info(
                "Expired sessions cleaned up",
                extra={"sessions_cleaned": count},
            )

            return count

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to cleanup expired sessions",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def is_session_valid(self, session_id: str) -> bool:
        """
        Check if session is valid.

        Validates that session exists, is active, and not expired.

        Args:
            session_id: Session identifier

        Returns:
            True if session is valid, False otherwise

        Example:
            >>> service = SessionService(db_session)
            >>> is_valid = await service.is_session_valid("session-123")
        """
        if not session_id:
            return False

        try:
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                logger.debug(
                    "Session not found",
                    extra={"session_id": session_id},
                )
                return False

            if not session.is_active:
                logger.debug(
                    "Session is not active",
                    extra={"session_id": session_id},
                )
                return False

            if session.expires_at < datetime.utcnow():
                logger.debug(
                    "Session is expired",
                    extra={
                        "session_id": session_id,
                        "expires_at": session.expires_at.isoformat(),
                    },
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Failed to validate session",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """
        Get session information.

        Returns comprehensive session details including device info and activity.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session information, or None if not found

        Example:
            >>> service = SessionService(db_session)
            >>> info = await service.get_session_info("session-123")
        """
        if not session_id:
            return None

        try:
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalars().first()

            if not session:
                return None

            return {
                "id": session.id,
                "user_id": session.user_id,
                "device_fingerprint": session.device_fingerprint,
                "user_agent": session.user_agent,
                "ip_address": session.ip_address,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "last_activity_at": session.last_activity_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "terminated_at": session.terminated_at.isoformat()
                if session.terminated_at
                else None,
                "metadata": session.metadata,
            }

        except Exception as e:
            logger.error(
                "Failed to get session info",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None
