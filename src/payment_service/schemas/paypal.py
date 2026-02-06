import logging
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class PayPalDepositRequest(BaseModel):
    """
    PayPal deposit payment request schema.

    Validates deposit payment parameters including amount, currency,
    and optional metadata for PayPal order creation.
    """

    wallet_id: str = Field(..., description="Wallet ID to deposit into", min_length=1)
    amount: Decimal = Field(..., description="Deposit amount", gt=0)
    currency: str = Field(
        default="USD",
        description="Currency code (USD, EUR, etc.)",
        min_length=3,
        max_length=3,
    )
    return_url: Optional[str] = Field(
        None,
        description="URL to redirect after payment approval",
        max_length=2000,
    )
    cancel_url: Optional[str] = Field(
        None,
        description="URL to redirect if payment is cancelled",
        max_length=2000,
    )
    description: Optional[str] = Field(
        None,
        description="Payment description",
        max_length=500,
    )
    metadata: Optional[dict[str, str]] = Field(
        default=None,
        description="Additional metadata for the payment",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate deposit amount is positive and has max 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")

        if v > Decimal("999999.99"):
            raise ValueError("Amount exceeds maximum allowed value")

        decimal_places = abs(v.as_tuple().exponent)
        if decimal_places > 2:
            raise ValueError("Amount can have at most 2 decimal places")

        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format."""
        if not v:
            raise ValueError("Currency is required")

        v = v.upper()

        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "MXN", "BRL"}
        if v not in valid_currencies:
            raise ValueError(
                f"Currency must be one of: {', '.join(sorted(valid_currencies))}"
            )

        return v

    @field_validator("wallet_id")
    @classmethod
    def validate_wallet_id(cls, v: str) -> str:
        """Validate wallet ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Wallet ID cannot be empty")
        return v.strip()

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
        """Validate metadata dictionary."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")

        if len(v) > 50:
            raise ValueError("Metadata can contain at most 50 keys")

        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Metadata keys and values must be strings")

            if len(key) > 40:
                raise ValueError("Metadata keys must be at most 40 characters")

            if len(value) > 500:
                raise ValueError("Metadata values must be at most 500 characters")

        return v

    model_config = {"json_schema_extra": {"example": {"wallet_id": "wallet_123", "amount": 50.00, "currency": "USD", "description": "Deposit to account", "return_url": "https://example.com/success", "cancel_url": "https://example.com/cancel"}}}


class PayPalWithdrawRequest(BaseModel):
    """
    PayPal withdrawal/payout request schema.

    Validates withdrawal parameters including amount, currency,
    and PayPal account email for payout processing.
    """

    wallet_id: str = Field(..., description="Wallet ID to withdraw from", min_length=1)
    amount: Decimal = Field(..., description="Withdrawal amount", gt=0)
    currency: str = Field(
        default="USD",
        description="Currency code (USD, EUR, etc.)",
        min_length=3,
        max_length=3,
    )
    paypal_email: str = Field(
        ...,
        description="PayPal account email for payout",
        min_length=3,
        max_length=254,
    )
    note: Optional[str] = Field(
        None,
        description="Note for the recipient",
        max_length=1000,
    )
    metadata: Optional[dict[str, str]] = Field(
        default=None,
        description="Additional metadata for the withdrawal",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate withdrawal amount is positive and has max 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")

        if v > Decimal("999999.99"):
            raise ValueError("Amount exceeds maximum allowed value")

        decimal_places = abs(v.as_tuple().exponent)
        if decimal_places > 2:
            raise ValueError("Amount can have at most 2 decimal places")

        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format."""
        if not v:
            raise ValueError("Currency is required")

        v = v.upper()

        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "MXN", "BRL"}
        if v not in valid_currencies:
            raise ValueError(
                f"Currency must be one of: {', '.join(sorted(valid_currencies))}"
            )

        return v

    @field_validator("wallet_id")
    @classmethod
    def validate_wallet_id(cls, v: str) -> str:
        """Validate wallet ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Wallet ID cannot be empty")
        return v.strip()

    @field_validator("paypal_email")
    @classmethod
    def validate_paypal_email(cls, v: str) -> str:
        """Validate PayPal email format."""
        if not v or not v.strip():
            raise ValueError("PayPal email cannot be empty")

        v = v.strip().lower()

        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")

        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
        """Validate metadata dictionary."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")

        if len(v) > 50:
            raise ValueError("Metadata can contain at most 50 keys")

        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Metadata keys and values must be strings")

            if len(key) > 40:
                raise ValueError("Metadata keys must be at most 40 characters")

            if len(value) > 500:
                raise ValueError("Metadata values must be at most 500 characters")

        return v

    model_config = {"json_schema_extra": {"example": {"wallet_id": "wallet_123", "amount": 50.00, "currency": "USD", "paypal_email": "user@example.com", "note": "Withdrawal to PayPal"}}}


class PayPalPaymentResponse(BaseModel):
    """
    PayPal payment response schema.

    Contains payment information including payment ID, status,
    approval URL for front-end redirect, and metadata.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    payment_id: Optional[str] = Field(None, description="PayPal Order or Capture ID")
    approval_url: Optional[str] = Field(
        None,
        description="PayPal approval URL for front-end redirect",
    )
    status: Optional[str] = Field(None, description="Payment status")
    amount: Optional[Decimal] = Field(None, description="Payment amount", gt=0)
    currency: Optional[str] = Field(None, description="Payment currency code")
    transaction_id: Optional[str] = Field(
        None,
        description="Internal transaction ID",
    )
    payout_batch_id: Optional[str] = Field(
        None,
        description="PayPal payout batch ID for withdrawals",
    )
    error: Optional[dict[str, str]] = Field(
        None,
        description="Error information if operation failed",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional payment metadata",
    )

    model_config = {"json_schema_extra": {"example": {"success": True, "payment_id": "ORDER-123456789", "approval_url": "https://www.paypal.com/checkoutnow?token=ABC123", "status": "CREATED", "amount": 50.00, "currency": "USD"}}}


class PayPalIPNEvent(BaseModel):
    """
    PayPal IPN webhook event schema.

    Validates incoming PayPal webhook events including event type,
    event ID, and resource data payload.
    """

    id: str = Field(..., description="PayPal event ID", min_length=1)
    event_type: str = Field(..., description="PayPal event type", min_length=1)
    resource: dict[str, Any] = Field(..., description="Event resource data")
    create_time: Optional[str] = Field(None, description="Event creation timestamp")
    event_version: Optional[str] = Field(None, description="Event version")
    resource_type: Optional[str] = Field(None, description="Resource type")

    @field_validator("id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate event ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v.strip()

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type format."""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")

        v = v.strip()

        valid_event_types = {
            "PAYMENT.CAPTURE.COMPLETED",
            "PAYMENT.CAPTURE.DENIED",
            "PAYMENT.CAPTURE.REFUNDED",
            "PAYMENT.CAPTURE.REVERSED",
            "CHECKOUT.ORDER.APPROVED",
            "CHECKOUT.ORDER.COMPLETED",
            "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
            "PAYMENT.PAYOUTS-ITEM.FAILED",
            "PAYMENT.PAYOUTS-ITEM.DENIED",
            "CUSTOMER.DISPUTE.CREATED",
            "CUSTOMER.DISPUTE.RESOLVED",
            "CUSTOMER.DISPUTE.UPDATED",
        }

        if v not in valid_event_types:
            logger.warning(f"Unknown PayPal event type: {v}")

        return v

    @field_validator("resource")
    @classmethod
    def validate_resource(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate event resource payload."""
        if not isinstance(v, dict):
            raise ValueError("Event resource must be a dictionary")

        if "id" not in v:
            raise ValueError("Event resource must contain an 'id' field")

        return v

    model_config = {"json_schema_extra": {"example": {"id": "WH-123456789", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "CAPTURE-123", "amount": {"value": "50.00", "currency_code": "USD"}, "status": "COMPLETED"}, "create_time": "2023-01-01T00:00:00Z", "event_version": "1.0"}}}


class PayPalOAuthResponse(BaseModel):
    """
    PayPal OAuth token response schema.

    Contains OAuth access token and related information for
    PayPal API authentication.
    """

    access_token: str = Field(..., description="OAuth access token")
    token_type: str = Field(..., description="Token type (Bearer)")
    expires_in: int = Field(..., description="Token expiry time in seconds", gt=0)
    scope: Optional[str] = Field(None, description="OAuth scopes granted")
    nonce: Optional[str] = Field(None, description="OAuth nonce")

    @field_validator("access_token")
    @classmethod
    def validate_access_token(cls, v: str) -> str:
        """Validate access token is not empty."""
        if not v or not v.strip():
            raise ValueError("Access token cannot be empty")
        return v.strip()

    @field_validator("token_type")
    @classmethod
    def validate_token_type(cls, v: str) -> str:
        """Validate token type."""
        if v.upper() != "BEARER":
            logger.warning(f"Unexpected token type: {v}")
        return v

    model_config = {"json_schema_extra": {"example": {"access_token": "A21AAFEpH-9jsmn...", "token_type": "Bearer", "expires_in": 32400, "scope": "https://api.paypal.com/v1/payments/.* openid"}}}
