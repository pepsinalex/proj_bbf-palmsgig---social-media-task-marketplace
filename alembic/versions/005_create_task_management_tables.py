"""Create task management tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-05 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create platform enum
    op.execute(
        "CREATE TYPE platform_enum AS ENUM ("
        "'facebook', 'instagram', 'twitter', 'tiktok', 'youtube', 'linkedin'"
        ")"
    )

    # Create task type enum
    op.execute(
        "CREATE TYPE task_type_enum AS ENUM ("
        "'like', 'comment', 'share', 'follow', 'view', 'subscribe', 'engagement'"
        ")"
    )

    # Create task status enum
    op.execute(
        "CREATE TYPE task_status_enum AS ENUM ("
        "'draft', 'pending_payment', 'active', 'paused', 'completed', 'cancelled', 'expired'"
        ")"
    )

    # Create assignment status enum
    op.execute(
        "CREATE TYPE assignment_status_enum AS ENUM ("
        "'assigned', 'started', 'proof_submitted', 'in_review', 'approved', 'rejected', 'completed', 'cancelled'"
        ")"
    )

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM(
                "facebook",
                "instagram",
                "twitter",
                "tiktok",
                "youtube",
                "linkedin",
                create_type=False,
                name="platform_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "task_type",
            postgresql.ENUM(
                "like",
                "comment",
                "share",
                "follow",
                "view",
                "subscribe",
                "engagement",
                create_type=False,
                name="task_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("budget", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("service_fee", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "pending_payment",
                "active",
                "paused",
                "completed",
                "cancelled",
                "expired",
                create_type=False,
                name="task_status_enum",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("target_criteria", postgresql.JSON(), nullable=True),
        sa.Column("max_performers", sa.Integer(), nullable=False),
        sa.Column(
            "current_performers", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("budget > 0", name="check_budget_positive"),
        sa.CheckConstraint("service_fee >= 0", name="check_service_fee_non_negative"),
        sa.CheckConstraint("total_cost > 0", name="check_total_cost_positive"),
        sa.CheckConstraint("max_performers > 0", name="check_max_performers_positive"),
        sa.CheckConstraint(
            "current_performers >= 0", name="check_current_performers_non_negative"
        ),
        sa.CheckConstraint(
            "current_performers <= max_performers",
            name="check_current_performers_within_max",
        ),
    )

    # Create indexes for tasks table
    op.create_index("ix_tasks_creator_id", "tasks", ["creator_id"])
    op.create_index("ix_tasks_platform", "tasks", ["platform"])
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_expires_at", "tasks", ["expires_at"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    # Composite indexes for common queries
    op.create_index("idx_task_creator_status", "tasks", ["creator_id", "status"])
    op.create_index("idx_task_platform_status", "tasks", ["platform", "status"])
    op.create_index("idx_task_type_status", "tasks", ["task_type", "status"])
    op.create_index("idx_task_status_expires", "tasks", ["status", "expires_at"])
    op.create_index("idx_task_created", "tasks", ["created_at"])

    # Create task_assignments table
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("performer_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "assigned",
                "started",
                "proof_submitted",
                "in_review",
                "approved",
                "rejected",
                "completed",
                "cancelled",
                create_type=False,
                name="assignment_status_enum",
            ),
            nullable=False,
            server_default="assigned",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proof_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
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
            "(rating IS NULL) OR (rating >= 1 AND rating <= 5)",
            name="check_rating_range",
        ),
    )

    # Create indexes for task_assignments table
    op.create_index("ix_task_assignments_task_id", "task_assignments", ["task_id"])
    op.create_index(
        "ix_task_assignments_performer_id", "task_assignments", ["performer_id"]
    )
    op.create_index("ix_task_assignments_status", "task_assignments", ["status"])
    op.create_index(
        "ix_task_assignments_assigned_at", "task_assignments", ["assigned_at"]
    )

    # Unique constraint and composite indexes
    op.create_index(
        "idx_unique_task_performer",
        "task_assignments",
        ["task_id", "performer_id"],
        unique=True,
    )
    op.create_index(
        "idx_assignment_performer_status",
        "task_assignments",
        ["performer_id", "status"],
    )
    op.create_index(
        "idx_assignment_task_status", "task_assignments", ["task_id", "status"]
    )

    # Create task_history table
    op.create_table(
        "task_history",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(length=50), nullable=False),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("changed_by", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for task_history table
    op.create_index("ix_task_history_task_id", "task_history", ["task_id"])
    op.create_index("ix_task_history_new_status", "task_history", ["new_status"])
    op.create_index("ix_task_history_changed_by", "task_history", ["changed_by"])
    op.create_index("ix_task_history_created_at", "task_history", ["created_at"])

    # Composite indexes for audit queries
    op.create_index(
        "idx_history_task_created", "task_history", ["task_id", "created_at"]
    )
    op.create_index(
        "idx_history_changed_by_created", "task_history", ["changed_by", "created_at"]
    )
    op.create_index(
        "idx_history_new_status_created",
        "task_history",
        ["new_status", "created_at"],
    )


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop tables
    op.drop_table("task_history")
    op.drop_table("task_assignments")
    op.drop_table("tasks")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS assignment_status_enum")
    op.execute("DROP TYPE IF EXISTS task_status_enum")
    op.execute("DROP TYPE IF EXISTS task_type_enum")
    op.execute("DROP TYPE IF EXISTS platform_enum")
