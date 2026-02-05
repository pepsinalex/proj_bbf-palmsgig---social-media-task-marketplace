"""
Transaction Pydantic Schemas.

Provides request/response schemas for transaction management API endpoints
with comprehensive validation and serialization.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.payment_service.models.transaction import TransactionStatus, TransactionType

logger = logging.getLogger(__name__)


class TransactionBase(BaseModel):
    """
    Base schema for transaction with common fields.

    Used as a foundation for create/update schemas.
    """

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=4,
        description="Transaction amount (must be positive)",
        examples=[100.5000],
    )

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Currency code (USD, NGN, GHS)",
        examples=["USD"],
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Transaction description",
        examples=["Deposit to wallet"],
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive."""
        if v <= 0:
            raise ValueError("amount must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency format."""
        v = v.upper()
        if v not in ["USD", "NGN", "GHS"]:
            raise ValueError("currency must be one of: USD, NGN, GHS")
        return v


class TransactionCreate(TransactionBase):
    """
    Schema for transaction creation request.

    Used when creating a new transaction.
    """

    wallet_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Wallet ID (UUID format)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    type: TransactionType = Field(
        ...,
        description="Transaction type",
        examples=["deposit"],
    )

    reference: str | None = Field(
        default=None,
        max_length=100,
        description="Unique transaction reference (auto-generated if not provided)",
        examples=["TXN-20240115-123456"],
    )

    gateway_reference: str | None = Field(
        default=None,
        max_length=255,
        description="External payment gateway reference",
        examples=["PAYSTACK-REF-123456"],
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional transaction metadata",
        examples=[{"source": "mobile_app", "device_id": "ABC123"}],
    )

    @field_validator("wallet_id")
    @classmethod
    def validate_wallet_id(cls, v: str) -> str:
        """Validate wallet_id format."""
        if not v or len(v) != 36:
            raise ValueError("wallet_id must be a valid UUID (36 characters)")
        return v


class TransactionUpdate(BaseModel):
    """
    Schema for transaction update request.

    Used for updating transaction status and gateway reference.
    """

    status: TransactionStatus | None = Field(
        default=None,
        description="Transaction status",
        examples=["completed"],
    )

    gateway_reference: str | None = Field(
        default=None,
        max_length=255,
        description="External payment gateway reference",
        examples=["PAYSTACK-REF-123456"],
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional transaction metadata",
        examples=[{"gateway_response": "success"}],
    )


class TransactionResponse(BaseModel):
    """
    Schema for transaction response.

    Returns transaction details with all fields.
    """

    id: str = Field(
        ...,
        description="Transaction ID (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    wallet_id: str = Field(
        ...,
        description="Wallet ID (UUID)",
        examples=["650e8400-e29b-41d4-a716-446655440000"],
    )

    type: str = Field(
        ...,
        description="Transaction type",
        examples=["deposit"],
    )

    amount: Decimal = Field(
        ...,
        description="Transaction amount",
        examples=[100.5000],
    )

    currency: str = Field(
        ...,
        description="Currency code",
        examples=["USD"],
    )

    status: str = Field(
        ...,
        description="Transaction status",
        examples=["completed"],
    )

    reference: str = Field(
        ...,
        description="Unique transaction reference",
        examples=["TXN-20240115-123456"],
    )

    gateway_reference: str | None = Field(
        default=None,
        description="External payment gateway reference",
        examples=["PAYSTACK-REF-123456"],
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional transaction metadata",
    )

    description: str | None = Field(
        default=None,
        description="Transaction description",
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
                "wallet_id": "650e8400-e29b-41d4-a716-446655440000",
                "type": "deposit",
                "amount": "100.5000",
                "currency": "USD",
                "status": "completed",
                "reference": "TXN-20240115-123456",
                "gateway_reference": "PAYSTACK-REF-123456",
                "metadata": {"source": "mobile_app"},
                "description": "Deposit to wallet",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class TransactionList(BaseModel):
    """
    Schema for paginated transaction list response.

    Returns a list of transactions with pagination metadata.
    """

    transactions: list[TransactionResponse] = Field(
        ...,
        description="List of transactions",
    )

    total: int = Field(
        ...,
        ge=0,
        description="Total number of transactions",
        examples=[100],
    )

    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
        examples=[1],
    )

    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page",
        examples=[20],
    )

    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        examples=[5],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "transactions": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "wallet_id": "650e8400-e29b-41d4-a716-446655440000",
                        "type": "deposit",
                        "amount": "100.5000",
                        "currency": "USD",
                        "status": "completed",
                        "reference": "TXN-20240115-123456",
                        "gateway_reference": "PAYSTACK-REF-123456",
                        "metadata": None,
                        "description": "Deposit to wallet",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        },
    }
