"""
Social media account Pydantic schemas for API operations.

This module provides Pydantic schemas for social account management including
account linking, OAuth callbacks, verification, and list operations with proper
validation and security considerations.
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.social_media.enums.platform_enums import Platform

logger = logging.getLogger(__name__)


class AccountLinkRequest(BaseModel):
    """
    Request schema for linking a social media account.

    Used to initiate OAuth flow for connecting a social media platform.
    Validates platform and optional custom scopes.

    Attributes:
        platform: Social media platform to link
        scopes: Optional custom OAuth scopes (uses platform defaults if not provided)
        redirect_uri: Optional custom redirect URI for OAuth callback
    """

    platform: str = Field(
        ...,
        description="Social media platform to link",
        min_length=1,
        max_length=50,
    )

    scopes: Optional[list[str]] = Field(
        default=None,
        description="Optional custom OAuth scopes",
    )

    redirect_uri: Optional[str] = Field(
        default=None,
        description="Optional custom redirect URI",
        max_length=500,
    )

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """
        Validate platform name is supported.

        Args:
            v: Platform name string

        Returns:
            Validated platform name in lowercase

        Raises:
            ValueError: If platform is not supported
        """
        normalized = v.lower().strip()
        if not Platform.validate(normalized):
            valid_platforms = ", ".join([p.value for p in Platform])
            logger.warning(
                "Invalid platform in link request",
                extra={"platform": v, "valid_platforms": valid_platforms},
            )
            raise ValueError(
                f"Invalid platform: {v}. Valid platforms: {valid_platforms}"
            )
        return normalized

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """
        Validate OAuth scopes format.

        Args:
            v: List of scope strings

        Returns:
            Validated scopes list

        Raises:
            ValueError: If scopes are invalid
        """
        if v is None:
            return None

        if not isinstance(v, list):
            raise ValueError("Scopes must be a list of strings")

        if len(v) == 0:
            return None

        for scope in v:
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError("Each scope must be a non-empty string")

        return [scope.strip() for scope in v]

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "platform": "facebook",
                "scopes": ["email", "public_profile", "pages_show_list"],
                "redirect_uri": "https://palmsgig.com/auth/callback",
            }
        }


class AccountLinkResponse(BaseModel):
    """
    Response schema for account linking initiation.

    Provides OAuth authorization URL and state token for CSRF protection.
    Does not expose any sensitive tokens.

    Attributes:
        authorization_url: OAuth authorization URL to redirect user
        state: CSRF protection state token
        platform: Social media platform being linked
    """

    authorization_url: str = Field(
        ...,
        description="OAuth authorization URL",
    )

    state: str = Field(
        ...,
        description="CSRF protection state token",
    )

    platform: str = Field(
        ...,
        description="Social media platform",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "authorization_url": "https://www.facebook.com/v18.0/dialog/oauth?client_id=...",
                "state": "abc123def456",
                "platform": "facebook",
            }
        }


class OAuthCallback(BaseModel):
    """
    OAuth callback parameters schema.

    Captures OAuth provider callback parameters including authorization code
    and state for token exchange.

    Attributes:
        code: Authorization code from OAuth provider
        state: State token for CSRF validation
        error: Optional error code from OAuth provider
        error_description: Optional error description
    """

    code: Optional[str] = Field(
        default=None,
        description="Authorization code",
        max_length=1000,
    )

    state: str = Field(
        ...,
        description="State token for CSRF validation",
        min_length=1,
        max_length=500,
    )

    error: Optional[str] = Field(
        default=None,
        description="OAuth error code",
        max_length=100,
    )

    error_description: Optional[str] = Field(
        default=None,
        description="OAuth error description",
        max_length=500,
    )

    @field_validator("code", "state")
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate string fields are not empty if provided.

        Args:
            v: String value

        Returns:
            Validated string

        Raises:
            ValueError: If value is empty string
        """
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Value cannot be empty string")
            return stripped
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "code": "AQD1x2y3z4...",
                "state": "abc123def456",
            }
        }


class AccountInfo(BaseModel):
    """
    Social media account information schema.

    Provides account details without exposing sensitive tokens.
    Used in API responses for account listing and details.

    Attributes:
        id: Account record ID
        platform: Social media platform
        account_id: Platform-specific account ID
        username: Platform username/handle
        display_name: Display name on platform
        is_verified: Account verification status
        last_verified_at: Last verification timestamp
        expires_at: Token expiration timestamp
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(
        ...,
        description="Account record ID",
    )

    platform: str = Field(
        ...,
        description="Social media platform",
    )

    account_id: str = Field(
        ...,
        description="Platform-specific account ID",
    )

    username: Optional[str] = Field(
        default=None,
        description="Platform username/handle",
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Display name on platform",
    )

    is_verified: bool = Field(
        ...,
        description="Account verification status",
    )

    last_verified_at: Optional[datetime] = Field(
        default=None,
        description="Last verification timestamp",
    )

    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp",
    )

    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
    )

    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    @property
    def is_token_expired(self) -> bool:
        """
        Check if access token is expired.

        Returns:
            True if token is expired or expiration time is not set
        """
        if self.expires_at is None:
            return True
        return self.expires_at <= datetime.utcnow()

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "platform": "facebook",
                "account_id": "1234567890",
                "username": "john_doe",
                "display_name": "John Doe",
                "is_verified": True,
                "last_verified_at": "2024-02-05T10:30:00Z",
                "expires_at": "2024-02-06T10:30:00Z",
                "created_at": "2024-02-01T10:30:00Z",
                "updated_at": "2024-02-05T10:30:00Z",
            }
        }


class AccountList(BaseModel):
    """
    List of social media accounts schema.

    Response schema for account listing with total count.

    Attributes:
        accounts: List of account information
        total: Total number of accounts
    """

    accounts: list[AccountInfo] = Field(
        ...,
        description="List of social media accounts",
    )

    total: int = Field(
        ...,
        description="Total number of accounts",
        ge=0,
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "accounts": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "platform": "facebook",
                        "account_id": "1234567890",
                        "username": "john_doe",
                        "display_name": "John Doe",
                        "is_verified": True,
                        "last_verified_at": "2024-02-05T10:30:00Z",
                        "expires_at": "2024-02-06T10:30:00Z",
                        "created_at": "2024-02-01T10:30:00Z",
                        "updated_at": "2024-02-05T10:30:00Z",
                    }
                ],
                "total": 1,
            }
        }


class AccountVerificationResponse(BaseModel):
    """
    Account verification response schema.

    Response for account verification operations.

    Attributes:
        account_id: Account record ID
        platform: Social media platform
        is_verified: Verification status
        verified_at: Verification timestamp
        message: Success message
    """

    account_id: str = Field(
        ...,
        description="Account record ID",
    )

    platform: str = Field(
        ...,
        description="Social media platform",
    )

    is_verified: bool = Field(
        ...,
        description="Verification status",
    )

    verified_at: Optional[datetime] = Field(
        default=None,
        description="Verification timestamp",
    )

    message: str = Field(
        ...,
        description="Success message",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "platform": "facebook",
                "is_verified": True,
                "verified_at": "2024-02-05T10:30:00Z",
                "message": "Account verified successfully",
            }
        }


class AccountDisconnectResponse(BaseModel):
    """
    Account disconnect response schema.

    Response for account disconnection operations.

    Attributes:
        account_id: Account record ID
        platform: Social media platform
        message: Success message
    """

    account_id: str = Field(
        ...,
        description="Account record ID",
    )

    platform: str = Field(
        ...,
        description="Social media platform",
    )

    message: str = Field(
        ...,
        description="Success message",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "platform": "facebook",
                "message": "Account disconnected successfully",
            }
        }
