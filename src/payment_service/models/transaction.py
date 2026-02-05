"""
Transaction model for tracking all financial operations.

This module provides the Transaction model for recording all payment activities
including deposits, withdrawals, transfers, payments, and refunds with proper
audit trail and encryption support.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

logger = logging.getLogger(__name__)


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(BaseModel):
    """
    Transaction model for tracking financial operations.

    Attributes:
        wallet_id: Foreign key reference to wallet
        type: Transaction type (deposit, withdrawal, transfer, payment, refund)
        amount: Transaction amount with proper decimal precision (19,4)
        currency: Currency code (USD, NGN, GHS)
        status: Transaction status (pending, processing, completed, failed, cancelled)
        reference: Unique transaction reference for idempotency
        gateway_reference: External payment gateway reference ID
        metadata: JSON field for storing gateway responses and additional data
        description: Human-readable transaction description
    """

    __tablename__ = "transactions"

    wallet_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key reference to wallet",
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Transaction type",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        comment="Transaction amount",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        comment="Currency code",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TransactionStatus.PENDING.value,
        index=True,
        comment="Transaction status",
    )

    reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique transaction reference",
    )

    gateway_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="External payment gateway reference",
    )

    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Gateway responses and additional data",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Transaction description",
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship(
        "Wallet",
        back_populates="transactions",
    )

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry",
        back_populates="transaction",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="check_transaction_amount_positive",
        ),
        CheckConstraint(
            f"type IN ('{TransactionType.DEPOSIT.value}', '{TransactionType.WITHDRAWAL.value}', '{TransactionType.TRANSFER.value}', '{TransactionType.PAYMENT.value}', '{TransactionType.REFUND.value}')",
            name="check_transaction_type_valid",
        ),
        CheckConstraint(
            f"status IN ('{TransactionStatus.PENDING.value}', '{TransactionStatus.PROCESSING.value}', '{TransactionStatus.COMPLETED.value}', '{TransactionStatus.FAILED.value}', '{TransactionStatus.CANCELLED.value}')",
            name="check_transaction_status_valid",
        ),
        Index("ix_transactions_wallet_id_status", "wallet_id", "status"),
        Index("ix_transactions_wallet_id_type", "wallet_id", "type"),
        Index("ix_transactions_status_type", "status", "type"),
        Index("ix_transactions_created_at_status", "created_at", "status"),
    )

    def __repr__(self) -> str:
        """Return string representation of the transaction."""
        return (
            f"<Transaction(id={self.id}, wallet_id={self.wallet_id}, "
            f"type={self.type}, amount={self.amount}, status={self.status}, "
            f"reference={self.reference})>"
        )

    def is_pending(self) -> bool:
        """
        Check if transaction is in pending status.

        Returns:
            True if status is pending
        """
        return self.status == TransactionStatus.PENDING.value

    def is_completed(self) -> bool:
        """
        Check if transaction is completed.

        Returns:
            True if status is completed
        """
        return self.status == TransactionStatus.COMPLETED.value

    def is_failed(self) -> bool:
        """
        Check if transaction failed.

        Returns:
            True if status is failed or cancelled
        """
        return self.status in [
            TransactionStatus.FAILED.value,
            TransactionStatus.CANCELLED.value,
        ]

    def mark_as_processing(self) -> None:
        """
        Update transaction status to processing.

        Raises:
            ValueError: If transaction is not in pending status
        """
        if self.status != TransactionStatus.PENDING.value:
            raise ValueError(
                f"Cannot mark as processing: current status is {self.status}"
            )

        self.status = TransactionStatus.PROCESSING.value
        logger.info(
            "Transaction marked as processing",
            extra={
                "transaction_id": self.id,
                "wallet_id": self.wallet_id,
                "reference": self.reference,
                "type": self.type,
            },
        )

    def mark_as_completed(self, gateway_reference: str | None = None) -> None:
        """
        Update transaction status to completed.

        Args:
            gateway_reference: Optional external gateway reference

        Raises:
            ValueError: If transaction is already completed or failed
        """
        if self.status in [
            TransactionStatus.COMPLETED.value,
            TransactionStatus.FAILED.value,
            TransactionStatus.CANCELLED.value,
        ]:
            raise ValueError(
                f"Cannot mark as completed: current status is {self.status}"
            )

        self.status = TransactionStatus.COMPLETED.value
        if gateway_reference:
            self.gateway_reference = gateway_reference

        logger.info(
            "Transaction marked as completed",
            extra={
                "transaction_id": self.id,
                "wallet_id": self.wallet_id,
                "reference": self.reference,
                "type": self.type,
                "gateway_reference": gateway_reference,
            },
        )

    def mark_as_failed(self, error_message: str | None = None) -> None:
        """
        Update transaction status to failed.

        Args:
            error_message: Optional error description

        Raises:
            ValueError: If transaction is already completed
        """
        if self.status == TransactionStatus.COMPLETED.value:
            raise ValueError("Cannot mark completed transaction as failed")

        self.status = TransactionStatus.FAILED.value
        if error_message:
            if not self.metadata:
                self.metadata = {}
            self.metadata["error"] = error_message

        logger.error(
            "Transaction marked as failed",
            extra={
                "transaction_id": self.id,
                "wallet_id": self.wallet_id,
                "reference": self.reference,
                "type": self.type,
                "error": error_message,
            },
        )

    def cancel(self) -> None:
        """
        Cancel pending transaction.

        Raises:
            ValueError: If transaction is not in pending status
        """
        if self.status != TransactionStatus.PENDING.value:
            raise ValueError(
                f"Cannot cancel transaction with status {self.status}"
            )

        self.status = TransactionStatus.CANCELLED.value
        logger.info(
            "Transaction cancelled",
            extra={
                "transaction_id": self.id,
                "wallet_id": self.wallet_id,
                "reference": self.reference,
                "type": self.type,
            },
        )
