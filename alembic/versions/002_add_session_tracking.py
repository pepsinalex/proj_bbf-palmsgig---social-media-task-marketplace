"""Add user_sessions table for session tracking

Revision ID: 002
Revises: 001
Create Date: 2026-02-05 14:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "user_sessions",
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
        sa.Column("refresh_token_jti", sa.String(length=100), nullable=False, unique=True),
        sa.Column("device_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "last_activity_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("terminated_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
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

    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index(
        "ix_user_sessions_refresh_token_jti", "user_sessions", ["refresh_token_jti"]
    )
    op.create_index(
        "ix_user_sessions_device_fingerprint", "user_sessions", ["device_fingerprint"]
    )
    op.create_index("ix_user_sessions_ip_address", "user_sessions", ["ip_address"])
    op.create_index("ix_user_sessions_is_active", "user_sessions", ["is_active"])
    op.create_index(
        "ix_user_sessions_last_activity_at", "user_sessions", ["last_activity_at"]
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index(
        "ix_user_sessions_user_active", "user_sessions", ["user_id", "is_active"]
    )
    op.create_index(
        "ix_user_sessions_user_device",
        "user_sessions",
        ["user_id", "device_fingerprint"],
    )
    op.create_index(
        "ix_user_sessions_expiry", "user_sessions", ["expires_at", "is_active"]
    )

    op.execute("""
        ALTER TABLE refresh_tokens
        ADD COLUMN IF NOT EXISTS token_family VARCHAR(100),
        ADD COLUMN IF NOT EXISTS revoked_reason VARCHAR(255),
        ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500),
        ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45),
        ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP;
    """)

    op.create_index("ix_refresh_tokens_token_family", "refresh_tokens", ["token_family"])
    op.create_index(
        "ix_refresh_tokens_ip_address", "refresh_tokens", ["ip_address"]
    )
    op.create_index(
        "ix_refresh_tokens_last_used_at", "refresh_tokens", ["last_used_at"]
    )
    op.create_index(
        "ix_refresh_tokens_user_active", "refresh_tokens", ["user_id", "is_revoked"]
    )
    op.create_index(
        "ix_refresh_tokens_token_active", "refresh_tokens", ["token", "is_revoked"]
    )
    op.create_index(
        "ix_refresh_tokens_expiry", "refresh_tokens", ["expires_at", "is_revoked"]
    )
    op.create_index(
        "ix_refresh_tokens_family", "refresh_tokens", ["token_family", "is_revoked"]
    )

    op.execute("""
        ALTER TABLE authentication_methods
        ADD COLUMN IF NOT EXISTS scope VARCHAR(500),
        ADD COLUMN IF NOT EXISTS provider_data JSON,
        ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP;
    """)

    op.create_index(
        "ix_authentication_methods_token_expires_at",
        "authentication_methods",
        ["token_expires_at"],
    )
    op.create_index(
        "ix_authentication_methods_last_used_at",
        "authentication_methods",
        ["last_used_at"],
    )
    op.create_index(
        "ix_auth_methods_user_provider",
        "authentication_methods",
        ["user_id", "provider"],
    )
    op.create_index(
        "ix_auth_methods_provider_user",
        "authentication_methods",
        ["provider", "provider_user_id"],
    )
    op.create_index(
        "ix_auth_methods_user_active",
        "authentication_methods",
        ["user_id", "is_active"],
    )

    op.execute("""
        ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'success',
        ADD COLUMN IF NOT EXISTS error_message TEXT,
        ADD COLUMN IF NOT EXISTS request_id VARCHAR(100),
        ADD COLUMN IF NOT EXISTS session_id VARCHAR(100),
        ADD COLUMN IF NOT EXISTS duration_ms INTEGER;
    """)

    op.create_index("ix_audit_logs_status", "audit_logs", ["status"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_session_id", "audit_logs", ["session_id"])
    op.create_index("ix_audit_logs_ip_address", "audit_logs", ["ip_address"])
    op.create_index(
        "ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"]
    )
    op.create_index("ix_audit_logs_action_status", "audit_logs", ["action", "status"])
    op.create_index(
        "ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"]
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_audit_logs_user_created", "audit_logs")
    op.drop_index("ix_audit_logs_action_status", "audit_logs")
    op.drop_index("ix_audit_logs_resource", "audit_logs")
    op.drop_index("ix_audit_logs_ip_address", "audit_logs")
    op.drop_index("ix_audit_logs_session_id", "audit_logs")
    op.drop_index("ix_audit_logs_request_id", "audit_logs")
    op.drop_index("ix_audit_logs_status", "audit_logs")

    op.execute("""
        ALTER TABLE audit_logs
        DROP COLUMN IF EXISTS status,
        DROP COLUMN IF EXISTS error_message,
        DROP COLUMN IF EXISTS request_id,
        DROP COLUMN IF EXISTS session_id,
        DROP COLUMN IF EXISTS duration_ms;
    """)

    op.drop_index("ix_auth_methods_user_active", "authentication_methods")
    op.drop_index("ix_auth_methods_provider_user", "authentication_methods")
    op.drop_index("ix_auth_methods_user_provider", "authentication_methods")
    op.drop_index(
        "ix_authentication_methods_last_used_at", "authentication_methods"
    )
    op.drop_index(
        "ix_authentication_methods_token_expires_at", "authentication_methods"
    )

    op.execute("""
        ALTER TABLE authentication_methods
        DROP COLUMN IF EXISTS scope,
        DROP COLUMN IF EXISTS provider_data,
        DROP COLUMN IF EXISTS last_used_at;
    """)

    op.drop_index("ix_refresh_tokens_family", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_expiry", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_active", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_active", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_last_used_at", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_ip_address", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_family", "refresh_tokens")

    op.execute("""
        ALTER TABLE refresh_tokens
        DROP COLUMN IF EXISTS token_family,
        DROP COLUMN IF EXISTS revoked_reason,
        DROP COLUMN IF EXISTS user_agent,
        DROP COLUMN IF EXISTS ip_address,
        DROP COLUMN IF EXISTS last_used_at;
    """)

    op.drop_index("ix_user_sessions_expiry", "user_sessions")
    op.drop_index("ix_user_sessions_user_device", "user_sessions")
    op.drop_index("ix_user_sessions_user_active", "user_sessions")
    op.drop_index("ix_user_sessions_expires_at", "user_sessions")
    op.drop_index("ix_user_sessions_last_activity_at", "user_sessions")
    op.drop_index("ix_user_sessions_is_active", "user_sessions")
    op.drop_index("ix_user_sessions_ip_address", "user_sessions")
    op.drop_index("ix_user_sessions_device_fingerprint", "user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_jti", "user_sessions")
    op.drop_index("ix_user_sessions_user_id", "user_sessions")

    op.drop_table("user_sessions")
