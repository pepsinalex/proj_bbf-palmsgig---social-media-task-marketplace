"""
Ledger Entry model for double-entry bookkeeping.

This module provides the LedgerEntry model implementing double-entry accounting
principles with immutable records for proper financial audit trails.
"""

import logging
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base, TimestampMixin

logger = logging.getLogger(__name__)


class AccountType(str, Enum):
    """Account type enumeration for double-entry bookkeeping."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class LedgerEntry(Base, TimestampMixin):
    """
    Ledger Entry model for double-entry bookkeeping.

    Implements immutable records for financial audit trail. Each transaction
    creates ledger entries following double-entry accounting principles.

    Attributes:
        id: Primary key (UUID string)
        transaction_id: Foreign key reference to transaction
        account_type: Account type (asset, liability, equity, revenue, expense)
        debit_amount: Debit amount with proper decimal precision (19,4)
        credit_amount: Credit amount with proper decimal precision (19,4)
        balance_after: Balance after this entry with proper decimal precision (19,4)
        description: Description of the ledger entry
    """

    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        comment="Primary key (UUID)",
    )

    transaction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key reference to transaction",
    )

    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Account type for double-entry bookkeeping",
    )

    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        default=Decimal("0.0000"),
        comment="Debit amount",
    )

    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        default=Decimal("0.0000"),
        comment="Credit amount",
    )

    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4),
        nullable=False,
        comment="Balance after this entry",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Ledger entry description",
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="ledger_entries",
    )

    __table_args__ = (
        CheckConstraint(
            "debit_amount >= 0",
            name="check_ledger_debit_amount_non_negative",
        ),
        CheckConstraint(
            "credit_amount >= 0",
            name="check_ledger_credit_amount_non_negative",
        ),
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)",
            name="check_ledger_entry_single_side",
        ),
        CheckConstraint(
            f"account_type IN ('{AccountType.ASSET.value}', '{AccountType.LIABILITY.value}', '{AccountType.EQUITY.value}', '{AccountType.REVENUE.value}', '{AccountType.EXPENSE.value}')",
            name="check_ledger_account_type_valid",
        ),
        Index("ix_ledger_entries_transaction_id_account_type", "transaction_id", "account_type"),
        Index("ix_ledger_entries_account_type_created_at", "account_type", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of the ledger entry."""
        return (
            f"<LedgerEntry(id={self.id}, transaction_id={self.transaction_id}, "
            f"account_type={self.account_type}, debit={self.debit_amount}, "
            f"credit={self.credit_amount}, balance={self.balance_after})>"
        )

    def __setattr__(self, name: str, value: object) -> None:
        """
        Override setattr to enforce immutability after creation.

        Raises:
            AttributeError: If attempting to modify immutable fields after creation
        """
        immutable_fields = {
            "id",
            "transaction_id",
            "account_type",
            "debit_amount",
            "credit_amount",
            "balance_after",
            "description",
            "created_at",
        }

        if name in immutable_fields and hasattr(self, name) and name != "created_at":
            existing_value = getattr(self, name, None)
            if existing_value is not None:
                raise AttributeError(
                    f"Cannot modify immutable field '{name}' on LedgerEntry"
                )

        super().__setattr__(name, value)

    def is_debit(self) -> bool:
        """
        Check if this is a debit entry.

        Returns:
            True if debit_amount > 0
        """
        return self.debit_amount > 0

    def is_credit(self) -> bool:
        """
        Check if this is a credit entry.

        Returns:
            True if credit_amount > 0
        """
        return self.credit_amount > 0

    def get_amount(self) -> Decimal:
        """
        Get the entry amount (debit or credit).

        Returns:
            The non-zero amount (debit or credit)
        """
        return self.debit_amount if self.debit_amount > 0 else self.credit_amount

    @classmethod
    def create_debit_entry(
        cls,
        transaction_id: str,
        account_type: AccountType,
        amount: Decimal,
        balance_after: Decimal,
        description: str | None = None,
    ) -> "LedgerEntry":
        """
        Create a debit ledger entry.

        Args:
            transaction_id: Transaction ID
            account_type: Account type
            amount: Debit amount
            balance_after: Balance after this entry
            description: Optional description

        Returns:
            New LedgerEntry instance

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        import uuid

        entry = cls(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            account_type=account_type.value,
            debit_amount=amount,
            credit_amount=Decimal("0.0000"),
            balance_after=balance_after,
            description=description,
        )

        logger.info(
            "Created debit ledger entry",
            extra={
                "ledger_entry_id": entry.id,
                "transaction_id": transaction_id,
                "account_type": account_type.value,
                "debit_amount": str(amount),
                "balance_after": str(balance_after),
            },
        )

        return entry

    @classmethod
    def create_credit_entry(
        cls,
        transaction_id: str,
        account_type: AccountType,
        amount: Decimal,
        balance_after: Decimal,
        description: str | None = None,
    ) -> "LedgerEntry":
        """
        Create a credit ledger entry.

        Args:
            transaction_id: Transaction ID
            account_type: Account type
            amount: Credit amount
            balance_after: Balance after this entry
            description: Optional description

        Returns:
            New LedgerEntry instance

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        import uuid

        entry = cls(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            account_type=account_type.value,
            debit_amount=Decimal("0.0000"),
            credit_amount=amount,
            balance_after=balance_after,
            description=description,
        )

        logger.info(
            "Created credit ledger entry",
            extra={
                "ledger_entry_id": entry.id,
                "transaction_id": transaction_id,
                "account_type": account_type.value,
                "credit_amount": str(amount),
                "balance_after": str(balance_after),
            },
        )

        return entry
