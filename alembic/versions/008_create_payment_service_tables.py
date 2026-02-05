"""Create payment service tables for wallets, transactions, and ledger entries

Revision ID: 008
Revises: 007
Create Date: 2026-02-05 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create wallets table
    op.create_table(
        "wallets",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
            unique=True,
            comment="Foreign key reference to user",
        ),
        sa.Column(
            "balance",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
            comment="Available balance",
        ),
        sa.Column(
            "escrow_balance",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
            comment="Balance held in escrow",
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="USD",
            comment="Currency code",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
            comment="Wallet status",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "balance >= 0",
            name="check_wallet_balance_non_negative",
        ),
        sa.CheckConstraint(
            "escrow_balance >= 0",
            name="check_wallet_escrow_balance_non_negative",
        ),
        sa.CheckConstraint(
            "currency IN ('USD', 'NGN', 'GHS')",
            name="check_wallet_currency_valid",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'closed')",
            name="check_wallet_status_valid",
        ),
    )

    # Create indexes for wallets table
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])
    op.create_index("ix_wallets_status", "wallets", ["status"])
    op.create_index("ix_wallets_created_at", "wallets", ["created_at"])
    op.create_index("ix_wallets_user_id_status", "wallets", ["user_id", "status"])
    op.create_index("ix_wallets_status_currency", "wallets", ["status", "currency"])

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "wallet_id",
            sa.String(length=36),
            sa.ForeignKey("wallets.id", ondelete="CASCADE"),
            nullable=False,
            comment="Foreign key reference to wallet",
        ),
        sa.Column(
            "type",
            sa.String(length=20),
            nullable=False,
            comment="Transaction type",
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            comment="Transaction amount",
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            comment="Currency code",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Transaction status",
        ),
        sa.Column(
            "reference",
            sa.String(length=100),
            nullable=False,
            unique=True,
            comment="Unique transaction reference",
        ),
        sa.Column(
            "gateway_reference",
            sa.String(length=255),
            nullable=True,
            comment="External payment gateway reference",
        ),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Gateway responses and additional data",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Transaction description",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="check_transaction_amount_positive",
        ),
        sa.CheckConstraint(
            "type IN ('deposit', 'withdrawal', 'transfer', 'payment', 'refund')",
            name="check_transaction_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="check_transaction_status_valid",
        ),
    )

    # Create indexes for transactions table
    op.create_index("ix_transactions_wallet_id", "transactions", ["wallet_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_reference", "transactions", ["reference"])
    op.create_index("ix_transactions_gateway_reference", "transactions", ["gateway_reference"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])
    op.create_index(
        "ix_transactions_wallet_id_status",
        "transactions",
        ["wallet_id", "status"],
    )
    op.create_index(
        "ix_transactions_wallet_id_type",
        "transactions",
        ["wallet_id", "type"],
    )
    op.create_index(
        "ix_transactions_status_type",
        "transactions",
        ["status", "type"],
    )
    op.create_index(
        "ix_transactions_created_at_status",
        "transactions",
        ["created_at", "status"],
    )

    # Create ledger_entries table
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "transaction_id",
            sa.String(length=36),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
            comment="Foreign key reference to transaction",
        ),
        sa.Column(
            "account_type",
            sa.String(length=20),
            nullable=False,
            comment="Account type for double-entry bookkeeping",
        ),
        sa.Column(
            "debit_amount",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
            comment="Debit amount",
        ),
        sa.Column(
            "credit_amount",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default=sa.text("0.0000"),
            comment="Credit amount",
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            comment="Balance after this entry",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Ledger entry description",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "debit_amount >= 0",
            name="check_ledger_debit_amount_non_negative",
        ),
        sa.CheckConstraint(
            "credit_amount >= 0",
            name="check_ledger_credit_amount_non_negative",
        ),
        sa.CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)",
            name="check_ledger_entry_single_side",
        ),
        sa.CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="check_ledger_account_type_valid",
        ),
    )

    # Create indexes for ledger_entries table
    op.create_index("ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_entries_account_type", "ledger_entries", ["account_type"])
    op.create_index("ix_ledger_entries_created_at", "ledger_entries", ["created_at"])
    op.create_index(
        "ix_ledger_entries_transaction_id_account_type",
        "ledger_entries",
        ["transaction_id", "account_type"],
    )
    op.create_index(
        "ix_ledger_entries_account_type_created_at",
        "ledger_entries",
        ["account_type", "created_at"],
    )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop tables in reverse order (respecting foreign key dependencies)
    op.drop_table("ledger_entries")
    op.drop_table("transactions")
    op.drop_table("wallets")
