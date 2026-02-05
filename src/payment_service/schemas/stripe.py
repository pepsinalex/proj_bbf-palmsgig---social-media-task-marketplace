import logging
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class StripeDepositRequest(BaseModel):
    """
    Stripe deposit payment request schema.

    Validates deposit payment parameters including amount, currency,
    and optional metadata.
    """

    wallet_id: str = Field(..., description="Wallet ID to deposit into", min_length=1)
    amount: Decimal = Field(..., description="Deposit amount", gt=0)
    currency: str = Field(
        default="USD",
        description="Currency code (USD, EUR, etc.)",
        min_length=3,
        max_length=3,
    )
    payment_method: Optional[str] = Field(
        None,
        description="Stripe payment method ID (optional)",
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
    confirm: bool = Field(
        default=False,
        description="Whether to automatically confirm the payment",
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

        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"}
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

    model_config = {"json_schema_extra": {"example": {"wallet_id": "wallet_123", "amount": 50.00, "currency": "USD", "description": "Deposit to account", "confirm": False}}}


class StripePaymentResponse(BaseModel):
    """
    Stripe payment response schema.

    Contains payment information including payment ID, status,
    client secret for front-end confirmation, and metadata.
    """

    success: bool = Field(..., description="Whether the operation was successful")
    payment_id: Optional[str] = Field(None, description="Stripe Payment Intent ID")
    client_secret: Optional[str] = Field(
        None,
        description="Client secret for front-end payment confirmation",
    )
    status: Optional[str] = Field(None, description="Payment status")
    amount: Optional[Decimal] = Field(None, description="Payment amount", gt=0)
    currency: Optional[str] = Field(None, description="Payment currency code")
    transaction_id: Optional[str] = Field(
        None,
        description="Internal transaction ID",
    )
    error: Optional[dict[str, str]] = Field(
        None,
        description="Error information if operation failed",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional payment metadata",
    )

    model_config = {"json_schema_extra": {"example": {"success": True, "payment_id": "pi_123456789", "client_secret": "pi_123_secret_456", "status": "requires_payment_method", "amount": 50.00, "currency": "USD"}}}


class StripeWebhookEvent(BaseModel):
    """
    Stripe webhook event schema.

    Validates incoming Stripe webhook events including event type,
    event ID, and event data payload.
    """

    id: str = Field(..., description="Stripe event ID", min_length=1)
    type: str = Field(..., description="Stripe event type", min_length=1)
    data: dict[str, Any] = Field(..., description="Event data payload")
    created: Optional[int] = Field(None, description="Event creation timestamp")
    livemode: Optional[bool] = Field(None, description="Whether event is from live mode")
    api_version: Optional[str] = Field(None, description="Stripe API version")

    @field_validator("id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate event ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type format."""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")

        v = v.strip()

        valid_event_types = {
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "payment_intent.canceled",
            "payment_intent.created",
            "charge.succeeded",
            "charge.failed",
            "charge.refunded",
            "charge.dispute.created",
            "charge.dispute.updated",
            "charge.dispute.closed",
            "refund.created",
            "refund.updated",
        }

        if v not in valid_event_types:
            logger.warning(f"Unknown Stripe event type: {v}")

        return v

    @field_validator("data")
    @classmethod
    def validate_event_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate event data payload."""
        if not isinstance(v, dict):
            raise ValueError("Event data must be a dictionary")

        if "object" not in v:
            raise ValueError("Event data must contain an 'object' field")

        return v

    model_config = {"json_schema_extra": {"example": {"id": "evt_123456789", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123", "amount": 5000, "currency": "usd", "status": "succeeded"}}, "created": 1234567890, "livemode": False}}}


class StripeRefundRequest(BaseModel):
    """
    Stripe refund request schema.

    Validates refund parameters including payment ID, refund amount,
    and optional refund reason.
    """

    payment_id: str = Field(..., description="Stripe Payment Intent ID", min_length=1)
    amount: Optional[Decimal] = Field(
        None,
        description="Refund amount (None for full refund)",
        gt=0,
    )
    reason: Optional[str] = Field(
        None,
        description="Refund reason",
    )
    metadata: Optional[dict[str, str]] = Field(
        None,
        description="Additional refund metadata",
    )

    @field_validator("payment_id")
    @classmethod
    def validate_payment_id(cls, v: str) -> str:
        """Validate payment ID format."""
        if not v or not v.strip():
            raise ValueError("Payment ID cannot be empty")

        v = v.strip()

        if not (v.startswith("pi_") or v.startswith("ch_")):
            raise ValueError("Payment ID must start with 'pi_' or 'ch_'")

        return v

    @field_validator("amount")
    @classmethod
    def validate_refund_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate refund amount if provided."""
        if v is None:
            return v

        if v <= 0:
            raise ValueError("Refund amount must be positive")

        if v > Decimal("999999.99"):
            raise ValueError("Refund amount exceeds maximum allowed value")

        decimal_places = abs(v.as_tuple().exponent)
        if decimal_places > 2:
            raise ValueError("Refund amount can have at most 2 decimal places")

        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate refund reason."""
        if v is None:
            return v

        valid_reasons = {"requested_by_customer", "duplicate", "fraudulent"}
        if v not in valid_reasons:
            raise ValueError(
                f"Reason must be one of: {', '.join(sorted(valid_reasons))}"
            )

        return v

    model_config = {"json_schema_extra": {"example": {"payment_id": "pi_123456789", "amount": 50.00, "reason": "requested_by_customer"}}}
