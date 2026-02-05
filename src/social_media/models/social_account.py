"""
Social media account model with secure token storage.

This module defines the SocialAccount model for storing OAuth tokens and
social media account information with encryption for sensitive data.
"""

import base64
import logging
import os
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models.base import BaseModel
from src.social_media.enums.platform_enums import Platform

logger = logging.getLogger(__name__)


class SocialAccount(BaseModel):
    """
    Social media account model with OAuth token storage.

    Stores connected social media accounts, OAuth tokens (encrypted),
    account metadata, and verification status. Provides encryption/decryption
    methods for secure token storage.

    Attributes:
        user_id: User who owns this social media account
        platform: Social media platform (Facebook, Instagram, etc.)
        account_id: Platform-specific account/user ID
        username: Platform username/handle
        display_name: Display name on the platform
        access_token: Encrypted OAuth access token
        refresh_token: Encrypted OAuth refresh token
        expires_at: Access token expiration timestamp
        scope: OAuth scopes granted
        is_verified: Whether account ownership is verified
        last_verified_at: Last verification timestamp
        created_at: Account creation timestamp (from BaseModel)
        updated_at: Last update timestamp (from BaseModel)
    """

    __tablename__ = "social_accounts"

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="User who owns this social media account",
    )

    platform: Mapped[str] = mapped_column(
        Enum(
            Platform,
            name="platform_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
        comment="Social media platform",
    )

    account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Platform-specific account/user ID",
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Platform username/handle",
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Display name on the platform",
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
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Access token expiration timestamp",
    )

    scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="OAuth scopes granted (space-separated)",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether account ownership is verified",
    )

    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last verification timestamp",
    )

    __table_args__ = (
        Index("ix_social_accounts_user_platform", "user_id", "platform", unique=True),
        Index("ix_social_accounts_platform_account", "platform", "account_id", unique=True),
        Index("ix_social_accounts_user_verified", "user_id", "is_verified"),
        Index("ix_social_accounts_expires_at", "expires_at"),
    )

    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Get encryption key from environment variable.

        Returns:
            Encryption key as bytes

        Raises:
            ValueError: If encryption key is not configured

        Note:
            Key should be stored in SOCIAL_MEDIA_ENCRYPTION_KEY environment variable.
            Generate with: Fernet.generate_key()
        """
        key_str = os.getenv("SOCIAL_MEDIA_ENCRYPTION_KEY")
        if not key_str:
            logger.error("Encryption key not configured in environment")
            raise ValueError(
                "SOCIAL_MEDIA_ENCRYPTION_KEY environment variable is required "
                "for token encryption/decryption"
            )

        try:
            return base64.urlsafe_b64decode(key_str)
        except Exception as exc:
            logger.error("Invalid encryption key format", extra={"error": str(exc)})
            raise ValueError("Invalid encryption key format") from exc

    @staticmethod
    def encrypt_token(token: str) -> str:
        """
        Encrypt token value for secure storage.

        Args:
            token: Plain text token to encrypt

        Returns:
            Encrypted token as base64 string

        Raises:
            ValueError: If encryption fails

        Example:
            >>> encrypted = SocialAccount.encrypt_token("my_token")
            >>> len(encrypted) > 0
            True
        """
        try:
            key = SocialAccount._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = fernet.encrypt(token.encode())
            encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode()

            logger.debug("Token encrypted successfully")
            return encrypted_str
        except Exception as exc:
            logger.error("Token encryption failed", extra={"error": str(exc)})
            raise ValueError("Failed to encrypt token") from exc

    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """
        Decrypt encrypted token value.

        Args:
            encrypted_token: Encrypted token as base64 string

        Returns:
            Decrypted plain text token

        Raises:
            ValueError: If decryption fails

        Example:
            >>> encrypted = SocialAccount.encrypt_token("my_token")
            >>> decrypted = SocialAccount.decrypt_token(encrypted)
            >>> decrypted
            'my_token'
        """
        try:
            key = SocialAccount._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token)
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            decrypted_str = decrypted_bytes.decode()

            logger.debug("Token decrypted successfully")
            return decrypted_str
        except Exception as exc:
            logger.error("Token decryption failed", extra={"error": str(exc)})
            raise ValueError("Failed to decrypt token") from exc

    def get_access_token(self) -> str:
        """
        Get decrypted access token.

        Returns:
            Decrypted access token

        Raises:
            ValueError: If decryption fails

        Example:
            >>> account.get_access_token()
            'plain_text_token'
        """
        return self.decrypt_token(self.access_token)

    def get_refresh_token(self) -> Optional[str]:
        """
        Get decrypted refresh token if available.

        Returns:
            Decrypted refresh token or None if not set

        Raises:
            ValueError: If decryption fails

        Example:
            >>> account.get_refresh_token()
            'plain_text_refresh_token'
        """
        if self.refresh_token is None:
            return None
        return self.decrypt_token(self.refresh_token)

    def set_access_token(self, token: str) -> None:
        """
        Encrypt and store access token.

        Args:
            token: Plain text access token

        Raises:
            ValueError: If encryption fails

        Example:
            >>> account.set_access_token("new_token")
            >>> account.access_token != "new_token"  # Token is encrypted
            True
        """
        self.access_token = self.encrypt_token(token)
        logger.info(
            "Access token updated",
            extra={
                "account_id": self.id,
                "user_id": self.user_id,
                "platform": self.platform,
            },
        )

    def set_refresh_token(self, token: Optional[str]) -> None:
        """
        Encrypt and store refresh token.

        Args:
            token: Plain text refresh token or None to clear

        Raises:
            ValueError: If encryption fails

        Example:
            >>> account.set_refresh_token("new_refresh_token")
            >>> account.refresh_token != "new_refresh_token"
            True
        """
        if token is None:
            self.refresh_token = None
        else:
            self.refresh_token = self.encrypt_token(token)

        logger.info(
            "Refresh token updated",
            extra={
                "account_id": self.id,
                "user_id": self.user_id,
                "platform": self.platform,
                "has_refresh_token": token is not None,
            },
        )

    def update_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Update OAuth tokens and expiration time.

        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_at: New expiration timestamp (optional)

        Raises:
            ValueError: If encryption fails

        Example:
            >>> from datetime import datetime, timedelta
            >>> expires = datetime.utcnow() + timedelta(hours=1)
            >>> account.update_tokens("new_access", "new_refresh", expires)
        """
        self.set_access_token(access_token)
        self.set_refresh_token(refresh_token)
        self.expires_at = expires_at

        logger.info(
            "Tokens updated successfully",
            extra={
                "account_id": self.id,
                "user_id": self.user_id,
                "platform": self.platform,
                "has_refresh_token": refresh_token is not None,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )

    @property
    def is_token_expired(self) -> bool:
        """
        Check if access token is expired.

        Returns:
            True if token is expired or expiration time is not set

        Example:
            >>> account.is_token_expired
            False
        """
        if self.expires_at is None:
            return True
        return self.expires_at <= datetime.utcnow()

    def mark_verified(self) -> None:
        """
        Mark account as verified and update verification timestamp.

        Example:
            >>> account.mark_verified()
            >>> account.is_verified
            True
        """
        self.is_verified = True
        self.last_verified_at = datetime.utcnow()

        logger.info(
            "Social account verified",
            extra={
                "account_id": self.id,
                "user_id": self.user_id,
                "platform": self.platform,
            },
        )

    def mark_unverified(self) -> None:
        """
        Mark account as unverified.

        Example:
            >>> account.mark_unverified()
            >>> account.is_verified
            False
        """
        self.is_verified = False

        logger.info(
            "Social account marked unverified",
            extra={
                "account_id": self.id,
                "user_id": self.user_id,
                "platform": self.platform,
            },
        )

    def get_scopes_list(self) -> list[str]:
        """
        Get OAuth scopes as list.

        Returns:
            List of scope strings

        Example:
            >>> account.scope = "email profile posts"
            >>> account.get_scopes_list()
            ['email', 'profile', 'posts']
        """
        if not self.scope:
            return []
        return self.scope.split()

    def set_scopes_list(self, scopes: list[str]) -> None:
        """
        Set OAuth scopes from list.

        Args:
            scopes: List of scope strings

        Example:
            >>> account.set_scopes_list(["email", "profile"])
            >>> account.scope
            'email profile'
        """
        self.scope = " ".join(scopes) if scopes else None

    def __repr__(self) -> str:
        """
        Return string representation of the social account.

        Returns:
            String representation with class name, ID, platform, and user_id
        """
        return (
            f"<SocialAccount(id={self.id}, platform={self.platform}, "
            f"user_id={self.user_id}, username={self.username})>"
        )
