"""
Wallet Pydantic Schemas.

Provides request/response schemas for wallet management API endpoints
with comprehensive validation and serialization.
"""

import logging
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from src.payment_service.models.wallet import Currency, WalletStatus

logger = logging.getLogger(__name__)


class WalletCreate(BaseModel):
    """
    Schema for wallet creation request.

    Used when creating a new wallet for a user.
    """

    user_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="User ID (UUID format)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    currency: Currency = Field(
        default=Currency.USD,
        description="Wallet currency",
        examples=["USD"],
    )

    initial_balance: Decimal = Field(
        default=Decimal("0.0000"),
        ge=0,
        decimal_places=4,
        description="Initial wallet balance",
        examples=[0.0000],
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id format."""
        if not v or len(v) != 36:
            raise ValueError("user_id must be a valid UUID (36 characters)")
        return v

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance(cls, v: Decimal) -> Decimal:
        """Validate initial balance is non-negative."""
        if v < 0:
            raise ValueError("initial_balance must be non-negative")
        return v


class WalletUpdate(BaseModel):
    """
    Schema for wallet update request.

    Used for updating wallet status.
    """

    status: WalletStatus | None = Field(
        default=None,
        description="Wallet status",
        examples=["active"],
    )


class WalletResponse(BaseModel):
    """
    Schema for wallet response.

    Returns wallet details with all fields.
    """

    id: str = Field(
        ...,
        description="Wallet ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    user_id: str = Field(
        ...,
        description="User ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    balance: Decimal = Field(
        ...,
        description="Available balance",
        examples=[1000.5000],
    )

    escrow_balance: Decimal = Field(
        ...,
        description="Balance held in escrow",
        examples=[50.0000],
    )

    currency: str = Field(
        ...,
        description="Currency code",
        examples=["USD"],
    )

    status: str = Field(
        ...,
        description="Wallet status",
        examples=["active"],
    )

    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )

    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "650e8400-e29b-41d4-a716-446655440000",
                "balance": "1000.5000",
                "escrow_balance": "50.0000",
                "currency": "USD",
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class WalletBalance(BaseModel):
    """
    Schema for wallet balance response.

    Returns simplified balance information.
    """

    wallet_id: str = Field(
        ...,
        description="Wallet ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    user_id: str = Field(
        ...,
        description="User ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    balance: Decimal = Field(
        ...,
        description="Available balance",
        examples=[1000.5000],
    )

    escrow_balance: Decimal = Field(
        ...,
        description="Balance held in escrow",
        examples=[50.0000],
    )

    total_balance: Decimal = Field(
        ...,
        description="Total balance (available + escrow)",
        examples=[1050.5000],
    )

    currency: str = Field(
        ...,
        description="Currency code",
        examples=["USD"],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "650e8400-e29b-41d4-a716-446655440000",
                "balance": "1000.5000",
                "escrow_balance": "50.0000",
                "total_balance": "1050.5000",
                "currency": "USD",
            }
        },
    }
