"""
Escrow Schemas.

Pydantic schemas for escrow operations including hold requests,
release requests, and escrow status responses with validation.
"""

import logging
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class EscrowHoldRequest(BaseModel):
    """
    Request schema for holding funds in escrow.

    Attributes:
        task_id: Unique task identifier
        payer_wallet_id: Wallet ID of the task creator (payer)
        payee_wallet_id: Wallet ID of the task worker (payee)
        amount: Base payment amount for the task
        platform_fee_percentage: Platform fee as decimal (e.g., 0.05 for 5%)
    """

    task_id: str = Field(..., min_length=1, description="Task identifier")
    payer_wallet_id: str = Field(..., min_length=1, description="Payer wallet ID")
    payee_wallet_id: str = Field(..., min_length=1, description="Payee wallet ID")
    amount: Decimal = Field(..., gt=0, description="Base payment amount")
    platform_fee_percentage: Decimal = Field(
        default=Decimal("0.05"),
        ge=0,
        le=1,
        description="Platform fee percentage (0-1)",
    )

    model_config = {"json_schema_extra": {"example": {
        "task_id": "task_123456",
        "payer_wallet_id": "wallet_abc123",
        "payee_wallet_id": "wallet_xyz789",
        "amount": 100.00,
        "platform_fee_percentage": 0.05,
    }}}

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """
        Validate amount is positive and has valid precision.

        Args:
            v: Amount value

        Returns:
            Validated amount

        Raises:
            ValueError: If amount is invalid
        """
        if v <= 0:
            logger.error("Invalid escrow amount", extra={"amount": str(v)})
            raise ValueError("Amount must be greater than zero")

        # Ensure proper decimal precision (max 4 decimal places)
        if v.as_tuple().exponent < -4:
            logger.error(
                "Invalid decimal precision for amount",
                extra={"amount": str(v), "exponent": v.as_tuple().exponent},
            )
            raise ValueError("Amount cannot have more than 4 decimal places")

        return v

    @field_validator("platform_fee_percentage")
    @classmethod
    def validate_platform_fee_percentage(cls, v: Decimal) -> Decimal:
        """
        Validate platform fee percentage.

        Args:
            v: Platform fee percentage

        Returns:
            Validated percentage

        Raises:
            ValueError: If percentage is invalid
        """
        if not (0 <= v <= 1):
            logger.error(
                "Invalid platform fee percentage",
                extra={"platform_fee_percentage": str(v)},
            )
            raise ValueError("Platform fee percentage must be between 0 and 1")

        return v


class EscrowReleaseRequest(BaseModel):
    """
    Request schema for releasing funds from escrow.

    Attributes:
        task_id: Unique task identifier
        payer_wallet_id: Wallet ID of the task creator (payer)
        payee_wallet_id: Wallet ID of the task worker (payee)
        amount: Base payment amount to release
        platform_fee_percentage: Platform fee as decimal (e.g., 0.05 for 5%)
    """

    task_id: str = Field(..., min_length=1, description="Task identifier")
    payer_wallet_id: str = Field(..., min_length=1, description="Payer wallet ID")
    payee_wallet_id: str = Field(..., min_length=1, description="Payee wallet ID")
    amount: Decimal = Field(..., gt=0, description="Base payment amount")
    platform_fee_percentage: Decimal = Field(
        default=Decimal("0.05"),
        ge=0,
        le=1,
        description="Platform fee percentage (0-1)",
    )

    model_config = {"json_schema_extra": {"example": {
        "task_id": "task_123456",
        "payer_wallet_id": "wallet_abc123",
        "payee_wallet_id": "wallet_xyz789",
        "amount": 100.00,
        "platform_fee_percentage": 0.05,
    }}}

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """
        Validate amount is positive and has valid precision.

        Args:
            v: Amount value

        Returns:
            Validated amount

        Raises:
            ValueError: If amount is invalid
        """
        if v <= 0:
            logger.error("Invalid release amount", extra={"amount": str(v)})
            raise ValueError("Amount must be greater than zero")

        # Ensure proper decimal precision (max 4 decimal places)
        if v.as_tuple().exponent < -4:
            logger.error(
                "Invalid decimal precision for amount",
                extra={"amount": str(v), "exponent": v.as_tuple().exponent},
            )
            raise ValueError("Amount cannot have more than 4 decimal places")

        return v

    @field_validator("platform_fee_percentage")
    @classmethod
    def validate_platform_fee_percentage(cls, v: Decimal) -> Decimal:
        """
        Validate platform fee percentage.

        Args:
            v: Platform fee percentage

        Returns:
            Validated percentage

        Raises:
            ValueError: If percentage is invalid
        """
        if not (0 <= v <= 1):
            logger.error(
                "Invalid platform fee percentage",
                extra={"platform_fee_percentage": str(v)},
            )
            raise ValueError("Platform fee percentage must be between 0 and 1")

        return v


class EscrowResponse(BaseModel):
    """
    Response schema for escrow operations.

    Attributes:
        task_id: Unique task identifier
        payer_wallet_id: Wallet ID of the task creator (payer)
        payee_wallet_id: Wallet ID of the task worker (payee)
        amount: Base payment amount
        platform_fee: Calculated platform fee
        total_amount: Total amount held in escrow (amount + platform_fee)
        status: Escrow status (held, released, refunded)
        transaction_id: Associated transaction ID
    """

    task_id: str
    payer_wallet_id: str
    payee_wallet_id: str
    amount: Decimal
    platform_fee: Decimal
    total_amount: Decimal
    status: str = Field(..., description="Escrow status: held, released, refunded")
    transaction_id: str

    model_config = {"json_schema_extra": {"example": {
        "task_id": "task_123456",
        "payer_wallet_id": "wallet_abc123",
        "payee_wallet_id": "wallet_xyz789",
        "amount": 100.00,
        "platform_fee": 5.00,
        "total_amount": 105.00,
        "status": "held",
        "transaction_id": "txn_987654",
    }}}

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """
        Validate escrow status.

        Args:
            v: Status value

        Returns:
            Validated status

        Raises:
            ValueError: If status is invalid
        """
        valid_statuses = {"held", "released", "refunded"}
        if v not in valid_statuses:
            logger.error(
                "Invalid escrow status",
                extra={"status": v, "valid_statuses": list(valid_statuses)},
            )
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")

        return v
