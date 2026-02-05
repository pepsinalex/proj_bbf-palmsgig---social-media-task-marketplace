"""
User Management Schemas Package.

This module exports Pydantic schemas for API serialization and validation.
"""

from src.user_management.schemas.auth import (
    UserRegistration,
    UserResponse,
    VerificationRequest,
    VerificationResponse,
)
from src.user_management.schemas.oauth import (
    OAuthAuthorizationRequest,
    OAuthAuthorizationResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    SocialAccountResponse,
    AccountLinkRequest,
    AccountLinkResponse,
    AccountUnlinkRequest,
    AccountUnlinkResponse,
)

__all__ = [
    "UserRegistration",
    "UserResponse",
    "VerificationRequest",
    "VerificationResponse",
    "OAuthAuthorizationRequest",
    "OAuthAuthorizationResponse",
    "OAuthCallbackRequest",
    "OAuthCallbackResponse",
    "SocialAccountResponse",
    "AccountLinkRequest",
    "AccountLinkResponse",
    "AccountUnlinkRequest",
    "AccountUnlinkResponse",
]
