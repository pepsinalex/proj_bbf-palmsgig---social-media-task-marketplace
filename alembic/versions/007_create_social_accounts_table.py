"""Create social_accounts table with encrypted token fields

Revision ID: 007
Revises: 006
Create Date: 2026-02-05 16:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create platform_type enum if it doesn't exist yet
    # This enum is shared with task management tables, so check first
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE platform_type AS ENUM (
                'facebook', 'instagram', 'twitter', 'tiktok', 'linkedin', 'youtube'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # Create social_accounts table
    op.create_table(
        "social_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
            comment="User who owns this social media account",
        ),
        sa.Column(
            "platform",
            postgresql.ENUM(
                "facebook",
                "instagram",
                "twitter",
                "tiktok",
                "linkedin",
                "youtube",
                name="platform_type",
            ),
            nullable=False,
            comment="Social media platform",
        ),
        sa.Column(
            "account_id",
            sa.String(length=255),
            nullable=False,
            comment="Platform-specific account/user ID",
        ),
        sa.Column(
            "username",
            sa.String(length=255),
            nullable=True,
            comment="Platform username/handle",
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=True,
            comment="Display name on the platform",
        ),
        sa.Column(
            "access_token",
            sa.Text(),
            nullable=False,
            comment="Encrypted OAuth access token",
        ),
        sa.Column(
            "refresh_token",
            sa.Text(),
            nullable=True,
            comment="Encrypted OAuth refresh token",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Access token expiration timestamp",
        ),
        sa.Column(
            "scope",
            sa.Text(),
            nullable=True,
            comment="OAuth scopes granted (space-separated)",
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Whether account ownership is verified",
        ),
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last verification timestamp",
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
    )

    # Create indexes for social_accounts table
    # Single column indexes
    op.create_index("ix_social_accounts_user_id", "social_accounts", ["user_id"])
    op.create_index("ix_social_accounts_platform", "social_accounts", ["platform"])
    op.create_index("ix_social_accounts_account_id", "social_accounts", ["account_id"])
    op.create_index("ix_social_accounts_is_verified", "social_accounts", ["is_verified"])
    op.create_index("ix_social_accounts_expires_at", "social_accounts", ["expires_at"])

    # Composite unique indexes for data integrity
    # Ensure one platform account per user
    op.create_index(
        "ix_social_accounts_user_platform",
        "social_accounts",
        ["user_id", "platform"],
        unique=True,
    )

    # Ensure platform account_id is unique per platform
    op.create_index(
        "ix_social_accounts_platform_account",
        "social_accounts",
        ["platform", "account_id"],
        unique=True,
    )

    # Composite indexes for common queries
    # Query verified accounts by user
    op.create_index(
        "ix_social_accounts_user_verified",
        "social_accounts",
        ["user_id", "is_verified"],
    )

    # Query accounts by platform and verification status
    op.create_index(
        "ix_social_accounts_platform_verified",
        "social_accounts",
        ["platform", "is_verified"],
    )

    # Query expired tokens for refresh
    op.create_index(
        "ix_social_accounts_expires_soon",
        "social_accounts",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop social_accounts table
    op.drop_table("social_accounts")

    # Note: We do NOT drop the platform_type enum here because it may be
    # used by other tables (e.g., tasks table from migration 005).
    # The enum will be cleaned up when all dependent tables are dropped.
