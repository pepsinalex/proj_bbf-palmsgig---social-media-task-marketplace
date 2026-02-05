"""
OAuth 2.0 Authentication Schemas.

Pydantic models for OAuth authentication requests, responses, and account linking.
Supports Google, Facebook, and Twitter OAuth providers.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class OAuthAuthorizationRequest(BaseModel):
    """Schema for OAuth authorization URL request."""

    provider: Literal["google", "facebook", "twitter"] = Field(
        ...,
        description="OAuth provider name",
    )
    redirect_uri: Optional[str] = Field(
        None,
        description="Custom redirect URI (uses default if not provided)",
    )
    state: Optional[str] = Field(
        None,
        description="State parameter for CSRF protection",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        supported = {"google", "facebook", "twitter"}
        if v not in supported:
            raise ValueError(
                f"Provider '{v}' not supported. Supported providers: {', '.join(supported)}"
            )
        return v


class OAuthAuthorizationResponse(BaseModel):
    """Schema for OAuth authorization URL response."""

    authorization_url: str = Field(
        ...,
        description="OAuth provider authorization URL for user redirection",
    )
    state: Optional[str] = Field(
        None,
        description="State parameter for CSRF verification",
    )
    provider: str = Field(
        ...,
        description="OAuth provider name",
    )


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback request."""

    code: str = Field(
        ...,
        description="Authorization code from OAuth provider",
    )
    state: Optional[str] = Field(
        None,
        description="State parameter for CSRF verification",
    )
    provider: Literal["google", "facebook", "twitter"] = Field(
        ...,
        description="OAuth provider name",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        supported = {"google", "facebook", "twitter"}
        if v not in supported:
            raise ValueError(
                f"Provider '{v}' not supported. Supported providers: {', '.join(supported)}"
            )
        return v


class SocialAccountInfo(BaseModel):
    """Schema for social account information."""

    provider: str = Field(..., description="OAuth provider name")
    provider_user_id: str = Field(..., description="User ID from OAuth provider")
    email: Optional[str] = Field(None, description="Email from provider")
    name: Optional[str] = Field(None, description="Display name from provider")
    avatar_url: Optional[str] = Field(None, description="Avatar/profile picture URL")
    profile_url: Optional[str] = Field(None, description="Profile URL on provider platform")
    is_active: bool = Field(default=True, description="Whether account is active")
    last_used_at: Optional[datetime] = Field(
        None, description="Last time this account was used for authentication"
    )
    linked_at: datetime = Field(..., description="When account was linked")

    model_config = {"from_attributes": True}


class OAuthCallbackResponse(BaseModel):
    """Schema for OAuth callback response."""

    success: bool = Field(..., description="Whether OAuth authentication succeeded")
    message: str = Field(..., description="Response message")
    user_id: Optional[str] = Field(None, description="User ID (for existing users)")
    is_new_user: bool = Field(
        default=False, description="Whether this is a new user registration"
    )
    access_token: Optional[str] = Field(None, description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(
        None, description="Access token expiration time in seconds"
    )
    user: Optional[dict] = Field(None, description="User information")
    social_account: Optional[SocialAccountInfo] = Field(
        None, description="Linked social account information"
    )


class AccountLinkRequest(BaseModel):
    """Schema for linking social account to existing user."""

    provider: Literal["google", "facebook", "twitter"] = Field(
        ...,
        description="OAuth provider name",
    )
    code: str = Field(
        ...,
        description="Authorization code from OAuth provider",
    )
    state: Optional[str] = Field(
        None,
        description="State parameter for CSRF verification",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        supported = {"google", "facebook", "twitter"}
        if v not in supported:
            raise ValueError(
                f"Provider '{v}' not supported. Supported providers: {', '.join(supported)}"
            )
        return v


class AccountLinkResponse(BaseModel):
    """Schema for account linking response."""

    success: bool = Field(..., description="Whether account linking succeeded")
    message: str = Field(..., description="Response message")
    social_account: Optional[SocialAccountInfo] = Field(
        None, description="Linked social account information"
    )


class AccountUnlinkRequest(BaseModel):
    """Schema for unlinking social account."""

    provider: Literal["google", "facebook", "twitter"] = Field(
        ...,
        description="OAuth provider name to unlink",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        supported = {"google", "facebook", "twitter"}
        if v not in supported:
            raise ValueError(
                f"Provider '{v}' not supported. Supported providers: {', '.join(supported)}"
            )
        return v


class AccountUnlinkResponse(BaseModel):
    """Schema for account unlinking response."""

    success: bool = Field(..., description="Whether account unlinking succeeded")
    message: str = Field(..., description="Response message")
    provider: str = Field(..., description="Unlinked provider name")


class SocialAccountResponse(BaseModel):
    """Schema for listing user's social accounts."""

    accounts: list[SocialAccountInfo] = Field(
        default_factory=list, description="List of linked social accounts"
    )
    total: int = Field(default=0, description="Total number of linked accounts")


class OAuthTokenInfo(BaseModel):
    """Schema for OAuth token information."""

    provider: str = Field(..., description="OAuth provider name")
    has_access_token: bool = Field(..., description="Whether access token exists")
    has_refresh_token: bool = Field(..., description="Whether refresh token exists")
    expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")
    is_expired: bool = Field(..., description="Whether token is expired")
    scope: Optional[str] = Field(None, description="OAuth scopes granted")

    model_config = {"from_attributes": True}


class OAuthProviderInfo(BaseModel):
    """Schema for OAuth provider information."""

    provider: str = Field(..., description="OAuth provider name")
    display_name: str = Field(..., description="Human-readable provider name")
    is_configured: bool = Field(..., description="Whether provider is configured")
    is_available: bool = Field(..., description="Whether provider is available for use")
    authorization_url_template: Optional[str] = Field(
        None, description="Template for authorization URL"
    )


class OAuthProvidersListResponse(BaseModel):
    """Schema for listing available OAuth providers."""

    providers: list[OAuthProviderInfo] = Field(
        default_factory=list, description="List of available OAuth providers"
    )
    total: int = Field(default=0, description="Total number of providers")
