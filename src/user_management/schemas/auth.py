"""
Authentication and User Registration Schemas.

Pydantic models for user registration, verification, and API responses.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegistration(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=100, description="User password (min 8 characters)"
    )
    phone_number: str = Field(..., description="Phone number with country code")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength requirements.

        Password must contain:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """
        Validate phone number format.

        Expected format: +[country code][number] (e.g., +1234567890)
        """
        if not re.match(r"^\+\d{1,3}\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in international format: +[country code][number]"
            )
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username contains only alphanumeric characters and underscores."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only alphanumeric characters and underscores"
            )
        return v


class VerificationRequest(BaseModel):
    """Schema for email or phone verification request."""

    email: Optional[EmailStr] = Field(None, description="Email address to verify")
    phone_number: Optional[str] = Field(None, description="Phone number to verify")
    token: str = Field(..., min_length=6, max_length=10, description="Verification token")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v and not re.match(r"^\+\d{1,3}\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in international format: +[country code][number]"
            )
        return v

    def model_post_init(self, __context) -> None:
        """Validate that either email or phone_number is provided, but not both."""
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone_number must be provided")
        if self.email and self.phone_number:
            raise ValueError("Provide either email or phone_number, not both")


class VerificationResponse(BaseModel):
    """Schema for verification response."""

    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Response message")
    user_id: Optional[str] = Field(None, description="User ID if verification successful")


class UserResponse(BaseModel):
    """Schema for user data in API responses."""

    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    phone_number: str = Field(..., description="Phone number")
    email_verified: bool = Field(default=False, description="Email verification status")
    phone_verified: bool = Field(default=False, description="Phone verification status")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}
