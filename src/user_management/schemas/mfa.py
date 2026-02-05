"""
Pydantic schemas for MFA (Multi-Factor Authentication) operations.

Defines request and response models for MFA setup, verification,
backup codes, and SMS OTP operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MFASetupRequest(BaseModel):
    """Request model for initiating MFA setup."""

    model_config = {"from_attributes": True}


class MFASetupResponse(BaseModel):
    """Response model for MFA setup containing TOTP configuration."""

    secret: str = Field(..., description="TOTP secret key for manual entry")
    qr_code: str = Field(..., description="Base64-encoded QR code image data URL")
    backup_codes: list[str] = Field(..., description="List of backup recovery codes")

    model_config = {"from_attributes": True}


class MFAVerifyRequest(BaseModel):
    """Request model for verifying TOTP token during setup."""

    token: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit TOTP verification code",
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """
        Validate TOTP token format.

        Args:
            v: Token value

        Returns:
            Validated token

        Raises:
            ValueError: If token is not 6 digits
        """
        if not v.isdigit():
            raise ValueError("Token must contain only digits")
        if len(v) != 6:
            raise ValueError("Token must be exactly 6 digits")
        return v

    model_config = {"from_attributes": True}


class MFAVerifyResponse(BaseModel):
    """Response model for MFA verification result."""

    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Result message")

    model_config = {"from_attributes": True}


class MFADisableRequest(BaseModel):
    """Request model for disabling MFA."""

    token: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit TOTP verification code",
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """
        Validate TOTP token format.

        Args:
            v: Token value

        Returns:
            Validated token

        Raises:
            ValueError: If token is not 6 digits
        """
        if not v.isdigit():
            raise ValueError("Token must contain only digits")
        if len(v) != 6:
            raise ValueError("Token must be exactly 6 digits")
        return v

    model_config = {"from_attributes": True}


class RecoveryCodesResponse(BaseModel):
    """Response model for backup recovery codes."""

    backup_codes: list[str] = Field(..., description="List of backup recovery codes")
    generated_at: datetime = Field(..., description="Timestamp when codes were generated")

    model_config = {"from_attributes": True}


class SMSOTPRequest(BaseModel):
    """Request model for sending SMS OTP."""

    resend: bool = Field(default=False, description="Whether this is a resend request")

    model_config = {"from_attributes": True}


class SMSOTPResponse(BaseModel):
    """Response model for SMS OTP send operation."""

    success: bool = Field(..., description="Whether SMS was sent successfully")
    message: str = Field(..., description="Result message")
    phone_last_digits: Optional[str] = Field(
        None, description="Last 4 digits of phone number"
    )
    expires_in: Optional[int] = Field(None, description="OTP expiry time in seconds")

    model_config = {"from_attributes": True}


class SMSOTPVerifyRequest(BaseModel):
    """Request model for verifying SMS OTP."""

    otp: str = Field(..., min_length=6, max_length=6, description="6-digit SMS OTP code")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """
        Validate OTP format.

        Args:
            v: OTP value

        Returns:
            Validated OTP

        Raises:
            ValueError: If OTP is not 6 digits
        """
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v

    model_config = {"from_attributes": True}


class MFAStatusResponse(BaseModel):
    """Response model for MFA status information."""

    mfa_enabled: bool = Field(..., description="Whether MFA is enabled")
    totp_configured: bool = Field(..., description="Whether TOTP is configured")
    phone_verified: bool = Field(..., description="Whether phone is verified")
    sms_backup_available: bool = Field(..., description="Whether SMS backup is available")
    backup_codes_count: int = Field(..., description="Number of remaining backup codes")
    mfa_setup_at: Optional[str] = Field(None, description="MFA setup timestamp (ISO format)")

    model_config = {"from_attributes": True}


class BackupCodeVerifyRequest(BaseModel):
    """Request model for verifying backup recovery code."""

    code: str = Field(..., min_length=14, max_length=14, description="Backup code (XXXX-XXXX-XXXX)")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """
        Validate backup code format.

        Args:
            v: Backup code value

        Returns:
            Validated and normalized backup code

        Raises:
            ValueError: If code format is invalid
        """
        # Remove any whitespace
        code = v.strip().upper()

        # Check format: XXXX-XXXX-XXXX
        parts = code.split("-")
        if len(parts) != 3:
            raise ValueError("Backup code must be in format XXXX-XXXX-XXXX")

        for part in parts:
            if len(part) != 4:
                raise ValueError("Each segment must be exactly 4 characters")
            if not all(c.isalnum() for c in part):
                raise ValueError("Backup code must contain only alphanumeric characters")

        return code

    model_config = {"from_attributes": True}
