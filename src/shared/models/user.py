"""
User model with authentication fields.

This module defines the User model with authentication fields, verification status,
MFA settings, and profile data. Includes indexes for performance optimization.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

if TYPE_CHECKING:
    from src.shared.models.auth import (
        AuditLog,
        AuthenticationMethod,
        RefreshToken,
        UserSession,
    )


class User(BaseModel):
    """
    User model with authentication and profile fields.

    Stores user account information, authentication credentials, verification status,
    MFA settings, and profile data. Provides relationships to authentication-related models.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    phone_verified_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    totp_secret: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Encrypted TOTP secret for MFA",
    )

    backup_codes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted backup recovery codes for MFA",
    )

    mfa_setup_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when MFA was first enabled",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    profile_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    last_login_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    authentication_methods: Mapped[list["AuthenticationMethod"]] = relationship(
        "AuthenticationMethod",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_username_active", "username", "is_active"),
        Index("ix_users_phone_verified", "phone", "phone_verified"),
        Index("ix_users_email_verified", "email", "email_verified"),
        Index("ix_users_mfa_enabled_active", "mfa_enabled", "is_active"),
    )

    def __repr__(self) -> str:
        """
        Return string representation of the user.

        Returns:
            String representation with class name, ID, and email
        """
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def is_verified(self) -> bool:
        """
        Check if user has verified their email.

        Returns:
            True if email is verified, False otherwise
        """
        return self.email_verified

    @property
    def is_locked(self) -> bool:
        """
        Check if user account is currently locked.

        Returns:
            True if locked_until is set and in the future, False otherwise
        """
        if self.locked_until is None:
            return False
        return self.locked_until > datetime.utcnow()

    def lock_account(self, duration_minutes: int = 30) -> None:
        """
        Lock user account for specified duration.

        Args:
            duration_minutes: Number of minutes to lock the account
        """
        from datetime import timedelta

        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)

    def unlock_account(self) -> None:
        """
        Unlock user account by clearing locked_until timestamp.
        """
        self.locked_until = None
        self.failed_login_attempts = 0

    def increment_failed_login(self) -> None:
        """
        Increment failed login attempts counter.

        Locks account after 5 failed attempts.
        """
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)

    def reset_failed_login(self) -> None:
        """
        Reset failed login attempts counter.

        Called after successful login.
        """
        self.failed_login_attempts = 0
        self.locked_until = None

    def update_last_login(self, ip_address: str | None = None) -> None:
        """
        Update last login timestamp and IP address.

        Args:
            ip_address: IP address of the login request
        """
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address

    def mark_email_verified(self) -> None:
        """
        Mark email as verified and set verification timestamp.
        """
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()

    def mark_phone_verified(self) -> None:
        """
        Mark phone as verified and set verification timestamp.
        """
        self.phone_verified = True
        self.phone_verified_at = datetime.utcnow()

    def enable_mfa(self, totp_secret: str, backup_codes: str) -> None:
        """
        Enable MFA for the user account.

        Args:
            totp_secret: Encrypted TOTP secret key
            backup_codes: Encrypted backup recovery codes
        """
        self.mfa_enabled = True
        self.totp_secret = totp_secret
        self.backup_codes = backup_codes
        self.mfa_setup_at = datetime.utcnow()

    def disable_mfa(self) -> None:
        """
        Disable MFA for the user account.
        """
        self.mfa_enabled = False
        self.totp_secret = None
        self.backup_codes = None
        self.mfa_setup_at = None

    def deactivate(self) -> None:
        """
        Deactivate user account.
        """
        self.is_active = False

    def activate(self) -> None:
        """
        Activate user account.
        """
        self.is_active = True
