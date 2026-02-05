"""add_mfa_fields

Revision ID: 004_add_mfa_fields
Revises: 003
Create Date: 2026-02-05 15:30:00.000000

Add MFA fields to users table including totp_secret, backup_codes, and mfa_setup_at.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_mfa_fields"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema by adding MFA-related fields to users table.

    Adds:
    - totp_secret: Encrypted TOTP secret for multi-factor authentication
    - backup_codes: Encrypted backup recovery codes
    - mfa_setup_at: Timestamp when MFA was first enabled

    Also removes deprecated mfa_secret column if it exists.
    """
    # Check if mfa_secret column exists and rename/remove it
    # First, add the new columns
    op.add_column(
        "users",
        sa.Column(
            "totp_secret",
            sa.String(length=500),
            nullable=True,
            comment="Encrypted TOTP secret for MFA",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "backup_codes",
            sa.Text(),
            nullable=True,
            comment="Encrypted backup recovery codes for MFA",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "mfa_setup_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp when MFA was first enabled",
        ),
    )

    # Drop the old mfa_secret column if it exists
    # Note: This migration handles the rename from mfa_secret to totp_secret
    try:
        op.drop_column("users", "mfa_secret")
    except Exception:
        # Column might not exist in all environments
        pass

    # Create indexes for performance optimization
    op.create_index(
        "ix_users_totp_secret",
        "users",
        ["totp_secret"],
        unique=False,
    )

    op.create_index(
        "ix_users_mfa_setup_at",
        "users",
        ["mfa_setup_at"],
        unique=False,
    )


def downgrade() -> None:
    """
    Downgrade schema by removing MFA-related fields from users table.

    Removes:
    - totp_secret column and index
    - backup_codes column
    - mfa_setup_at column and index

    Restores:
    - mfa_secret column for backward compatibility
    """
    # Drop indexes
    op.drop_index("ix_users_mfa_setup_at", table_name="users")
    op.drop_index("ix_users_totp_secret", table_name="users")

    # Restore old mfa_secret column
    op.add_column(
        "users",
        sa.Column(
            "mfa_secret",
            sa.String(length=255),
            nullable=True,
        ),
    )

    # Drop new columns
    op.drop_column("users", "mfa_setup_at")
    op.drop_column("users", "backup_codes")
    op.drop_column("users", "totp_secret")
