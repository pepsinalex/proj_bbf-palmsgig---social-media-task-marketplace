"""
Wallet model for managing user balances and multi-currency support.

This module provides the Wallet model for tracking user account balances,
escrow balances, and supporting multiple currencies with proper decimal precision.
"""

import logging
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

logger = logging.getLogger(__name__)


class WalletStatus(str, Enum):
    """Wallet status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Currency(str, Enum):
    """Supported currency enumeration."""

    USD = "USD"
    NGN = "NGN"
    GHS = "GHS"


class Wallet(BaseModel):
    """
    Wallet model for tracking user balances.

    Attributes:
        user_id: Foreign key reference to user
        balance: Available balance with proper decimal precision (19,4)
        escrow_balance: Balance held in escrow with proper decimal precision (19,4)
        currency: Currency code (USD, NGN, GHS)
        status: Wallet status (active, suspended, closed)
    """

    __tablename__ = "wallets"

    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key reference to user",
    )

    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        default=Decimal("0.0000"),
        comment="Available balance",
    )

    escrow_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        default=Decimal("0.0000"),
        comment="Balance held in escrow",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default=Currency.USD.value,
        comment="Currency code",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WalletStatus.ACTIVE.value,
        index=True,
        comment="Wallet status",
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="wallet",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="check_wallet_balance_non_negative",
        ),
        CheckConstraint(
            "escrow_balance >= 0",
            name="check_wallet_escrow_balance_non_negative",
        ),
        CheckConstraint(
            f"currency IN ('{Currency.USD.value}', '{Currency.NGN.value}', '{Currency.GHS.value}')",
            name="check_wallet_currency_valid",
        ),
        CheckConstraint(
            f"status IN ('{WalletStatus.ACTIVE.value}', '{WalletStatus.SUSPENDED.value}', '{WalletStatus.CLOSED.value}')",
            name="check_wallet_status_valid",
        ),
        Index("ix_wallets_user_id_status", "user_id", "status"),
        Index("ix_wallets_status_currency", "status", "currency"),
    )

    def __repr__(self) -> str:
        """Return string representation of the wallet."""
        return (
            f"<Wallet(id={self.id}, user_id={self.user_id}, "
            f"balance={self.balance}, currency={self.currency}, status={self.status})>"
        )

    def get_total_balance(self) -> Decimal:
        """
        Calculate total balance including escrow.

        Returns:
            Total balance (available + escrow)
        """
        return self.balance + self.escrow_balance

    def can_transact(self, amount: Decimal) -> bool:
        """
        Check if wallet can perform transaction with given amount.

        Args:
            amount: Amount to check

        Returns:
            True if wallet has sufficient balance and is active
        """
        if self.status != WalletStatus.ACTIVE.value:
            logger.warning(
                "Wallet transaction check failed: wallet not active",
                extra={
                    "wallet_id": self.id,
                    "user_id": self.user_id,
                    "status": self.status,
                },
            )
            return False

        if amount < 0:
            logger.warning(
                "Wallet transaction check failed: negative amount",
                extra={
                    "wallet_id": self.id,
                    "user_id": self.user_id,
                    "amount": str(amount),
                },
            )
            return False

        if self.balance < amount:
            logger.warning(
                "Wallet transaction check failed: insufficient balance",
                extra={
                    "wallet_id": self.id,
                    "user_id": self.user_id,
                    "balance": str(self.balance),
                    "required_amount": str(amount),
                },
            )
            return False

        return True

    def move_to_escrow(self, amount: Decimal) -> None:
        """
        Move funds from available balance to escrow.

        Args:
            amount: Amount to move to escrow

        Raises:
            ValueError: If amount is invalid or insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if self.balance < amount:
            raise ValueError(
                f"Insufficient balance: {self.balance} < {amount}"
            )

        self.balance -= amount
        self.escrow_balance += amount

        logger.info(
            "Moved funds to escrow",
            extra={
                "wallet_id": self.id,
                "user_id": self.user_id,
                "amount": str(amount),
                "new_balance": str(self.balance),
                "new_escrow_balance": str(self.escrow_balance),
            },
        )

    def release_from_escrow(self, amount: Decimal) -> None:
        """
        Release funds from escrow to available balance.

        Args:
            amount: Amount to release from escrow

        Raises:
            ValueError: If amount is invalid or insufficient escrow balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if self.escrow_balance < amount:
            raise ValueError(
                f"Insufficient escrow balance: {self.escrow_balance} < {amount}"
            )

        self.escrow_balance -= amount
        self.balance += amount

        logger.info(
            "Released funds from escrow",
            extra={
                "wallet_id": self.id,
                "user_id": self.user_id,
                "amount": str(amount),
                "new_balance": str(self.balance),
                "new_escrow_balance": str(self.escrow_balance),
            },
        )
