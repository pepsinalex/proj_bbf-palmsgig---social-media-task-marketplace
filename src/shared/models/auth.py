"""
Authentication-related models for methods, tokens, and audit logs.

This module defines authentication models including OAuth authentication methods,
refresh tokens for JWT, and audit logs for tracking user actions. Includes proper
relationships to User model and indexes for performance optimization.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

if TYPE_CHECKING:
    from src.shared.models.user import User


class AuthenticationMethod(BaseModel):
    """
    Authentication method model for OAuth providers.

    Stores OAuth authentication information for social login providers
    (Facebook, Google, Twitter, Instagram, etc.).
    """

    __tablename__ = "authentication_methods"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    access_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    scope: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    provider_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="authentication_methods",
    )

    __table_args__ = (
        Index("ix_auth_methods_user_provider", "user_id", "provider"),
        Index("ix_auth_methods_provider_user", "provider", "provider_user_id"),
        Index("ix_auth_methods_user_active", "user_id", "is_active"),
        Index("ix_auth_methods_token_expiry", "token_expires_at"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the authentication method.

        Returns:
            String representation with class name, ID, and provider
        """
        return f"<AuthenticationMethod(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

    @property
    def is_token_expired(self) -> bool:
        """
        Check if access token is expired.

        Returns:
            True if token_expires_at is in the past, False otherwise
        """
        if self.token_expires_at is None:
            return False
        return self.token_expires_at < datetime.utcnow()

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        """
        Update OAuth tokens.

        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_at: Token expiration timestamp (optional)
        """
        self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token
        self.token_expires_at = expires_at
        self.last_used_at = datetime.utcnow()

    def mark_as_used(self) -> None:
        """
        Update last used timestamp.
        """
        self.last_used_at = datetime.utcnow()

    def deactivate(self) -> None:
        """
        Deactivate the authentication method.
        """
        self.is_active = False

    def activate(self) -> None:
        """
        Activate the authentication method.
        """
        self.is_active = True


class RefreshToken(BaseModel):
    """
    Refresh token model for JWT authentication.

    Stores refresh tokens for JWT-based authentication with expiration
    and revocation support.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
    )

    token_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
        Index("ix_refresh_tokens_token_active", "token", "is_revoked"),
        Index("ix_refresh_tokens_expiry", "expires_at", "is_revoked"),
        Index("ix_refresh_tokens_family", "token_family", "is_revoked"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the refresh token.

        Returns:
            String representation with class name, ID, and user ID
        """
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"

    @property
    def is_expired(self) -> bool:
        """
        Check if refresh token is expired.

        Returns:
            True if expires_at is in the past, False otherwise
        """
        return self.expires_at < datetime.utcnow()

    @property
    def is_valid(self) -> bool:
        """
        Check if refresh token is valid (not revoked and not expired).

        Returns:
            True if token is valid, False otherwise
        """
        return not self.is_revoked and not self.is_expired

    def revoke(self, reason: str | None = None) -> None:
        """
        Revoke the refresh token.

        Args:
            reason: Optional reason for revocation
        """
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        if reason:
            self.revoked_reason = reason

    def mark_as_used(self) -> None:
        """
        Update last used timestamp.
        """
        self.last_used_at = datetime.utcnow()


class UserSession(BaseModel):
    """
    User session model for tracking active sessions.

    Stores session information including device fingerprinting, IP addresses,
    and activity tracking. Used for session management and security monitoring.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_jti: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    device_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    terminated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    session_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )

    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "is_active"),
        Index("ix_user_sessions_user_device", "user_id", "device_fingerprint"),
        Index("ix_user_sessions_jti", "refresh_token_jti"),
        Index("ix_user_sessions_expiry", "expires_at", "is_active"),
        Index("ix_user_sessions_activity", "last_activity_at"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the user session.

        Returns:
            String representation with class name, ID, and user ID
        """
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """
        Check if session is expired.

        Returns:
            True if expires_at is in the past, False otherwise
        """
        return self.expires_at < datetime.utcnow()

    @property
    def is_valid(self) -> bool:
        """
        Check if session is valid (active and not expired).

        Returns:
            True if session is valid, False otherwise
        """
        return self.is_active and not self.is_expired

    def terminate(self) -> None:
        """
        Terminate the session.
        """
        self.is_active = False
        self.terminated_at = datetime.utcnow()

    def update_activity(self, ip_address: str | None = None) -> None:
        """
        Update session activity timestamp.

        Args:
            ip_address: Optional updated IP address
        """
        self.last_activity_at = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address


class AuditLog(BaseModel):
    """
    Audit log model for tracking user actions.

    Records important user actions and system events for security auditing
    and compliance purposes.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    session_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    duration_ms: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="audit_logs",
    )

    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action_status", "action", "status"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the audit log.

        Returns:
            String representation with class name, ID, action, and user ID
        """
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id}, status={self.status})>"

    @classmethod
    def create_log(
        cls,
        action: str,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        duration_ms: int | None = None,
    ) -> "AuditLog":
        """
        Create audit log entry.

        Args:
            action: Action performed
            user_id: ID of user who performed the action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details as dictionary
            ip_address: IP address of the request
            user_agent: User agent string
            status: Status of the action (success, failure, error)
            error_message: Error message if action failed
            request_id: Request correlation ID
            session_id: Session ID
            duration_ms: Duration of operation in milliseconds

        Returns:
            New audit log instance
        """
        return cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            request_id=request_id,
            session_id=session_id,
            duration_ms=duration_ms,
        )


class OAuthToken(BaseModel):
    """
    OAuth token storage model for secure token management.

    Stores OAuth tokens with encryption for sensitive fields (access_token, refresh_token).
    Supports token expiration tracking and refresh token management.
    """

    __tablename__ = "oauth_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted OAuth access token",
    )

    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted OAuth refresh token",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
        comment="Access token expiration timestamp",
    )

    scope: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="OAuth scopes granted for this token",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="oauth_tokens",
    )

    __table_args__ = (
        Index("ix_oauth_tokens_user_provider", "user_id", "provider"),
        Index("ix_oauth_tokens_expires_at", "expires_at"),
        Index("ix_oauth_tokens_provider", "provider"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the OAuth token.

        Returns:
            String representation with class name, ID, provider, and user ID
        """
        return f"<OAuthToken(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """
        Check if access token is expired.

        Returns:
            True if expires_at is in the past, False otherwise
        """
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.utcnow()

    @property
    def is_valid(self) -> bool:
        """
        Check if token is valid (not expired).

        Returns:
            True if token is valid, False otherwise
        """
        return not self.is_expired

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        scope: str | None = None,
    ) -> None:
        """
        Update OAuth tokens and metadata.

        Args:
            access_token: New access token (encrypted)
            refresh_token: New refresh token (encrypted, optional)
            expires_at: Token expiration timestamp (optional)
            scope: OAuth scopes (optional)
        """
        self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token
        if expires_at is not None:
            self.expires_at = expires_at
        if scope is not None:
            self.scope = scope
        self.updated_at = datetime.utcnow()
