"""Add oauth_tokens table for secure OAuth token storage

Revision ID: 003
Revises: 002
Create Date: 2026-02-05 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create oauth_tokens table
    op.create_table(
        "oauth_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
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
            sa.DateTime(),
            nullable=True,
            comment="Access token expiration timestamp",
        ),
        sa.Column(
            "scope",
            sa.String(length=500),
            nullable=True,
            comment="OAuth scopes granted for this token",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # Create indexes for oauth_tokens
    op.create_index("ix_oauth_tokens_user_id", "oauth_tokens", ["user_id"])
    op.create_index("ix_oauth_tokens_provider", "oauth_tokens", ["provider"])
    op.create_index("ix_oauth_tokens_expires_at", "oauth_tokens", ["expires_at"])
    op.create_index(
        "ix_oauth_tokens_user_provider", "oauth_tokens", ["user_id", "provider"]
    )

    # Add comment to table
    op.execute("""
        COMMENT ON TABLE oauth_tokens IS 'OAuth token storage for secure token management with encryption';
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index("ix_oauth_tokens_user_provider", "oauth_tokens")
    op.drop_index("ix_oauth_tokens_expires_at", "oauth_tokens")
    op.drop_index("ix_oauth_tokens_provider", "oauth_tokens")
    op.drop_index("ix_oauth_tokens_user_id", "oauth_tokens")

    # Drop table
    op.drop_table("oauth_tokens")
