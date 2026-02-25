"""Add task search indexes for optimized discovery queries

Revision ID: 006
Revises: 005
Create Date: 2026-02-05 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Composite index for common filter combinations
    op.create_index(
        "ix_tasks_platform_status",
        "tasks",
        ["platform", "status"],
        postgresql_where=sa.text("status != 'draft'"),
    )

    # Composite index for budget-based queries with created_at ordering
    op.create_index(
        "ix_tasks_budget_created_at",
        "tasks",
        ["budget", "created_at"],
        postgresql_where=sa.text("status = 'active'"),
    )

    # Composite index for creator's tasks with status filter
    op.create_index(
        "ix_tasks_creator_id_status",
        "tasks",
        ["creator_id", "status"],
    )

    # Index for filtering by tasks with expiration set
    op.create_index(
        "ix_tasks_expires_at_not_null",
        "tasks",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # Index for available tasks (not full and not expired)
    op.create_index(
        "ix_tasks_available",
        "tasks",
        ["status", "current_performers", "max_performers"],
        postgresql_where=sa.text(
            "status = 'active' AND current_performers < max_performers"
        ),
    )

    # Composite index for task type and platform filtering
    op.create_index(
        "ix_tasks_task_type_platform",
        "tasks",
        ["task_type", "platform"],
    )

    # Index for budget range queries
    op.create_index(
        "ix_tasks_budget_range",
        "tasks",
        ["budget", "status"],
        postgresql_where=sa.text("status = 'active'"),
    )

    # Full-text search indexes for PostgreSQL
    # GIN index on title for text search
    op.execute(
        """
        CREATE INDEX ix_tasks_title_gin ON tasks
        USING gin(to_tsvector('english', title))
        """
    )

    # GIN index on description for text search
    op.execute(
        """
        CREATE INDEX ix_tasks_description_gin ON tasks
        USING gin(to_tsvector('english', description))
        """
    )

    # GIN index on instructions for text search
    op.execute(
        """
        CREATE INDEX ix_tasks_instructions_gin ON tasks
        USING gin(to_tsvector('english', instructions))
        """
    )

    # Composite GIN index for combined full-text search across all searchable fields
    op.execute(
        """
        CREATE INDEX ix_tasks_fulltext_search ON tasks
        USING gin(
            (setweight(to_tsvector('english', title), 'A') ||
             setweight(to_tsvector('english', description), 'B') ||
             setweight(to_tsvector('english', instructions), 'C'))
        )
        """
    )

    # Index for sorting by created_at (most recent first)
    op.create_index(
        "ix_tasks_created_at_desc",
        "tasks",
        [sa.text("created_at DESC")],
    )

    # Index for popularity/demand tracking
    op.create_index(
        "ix_tasks_current_performers",
        "tasks",
        ["current_performers", "max_performers"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index("ix_tasks_current_performers", table_name="tasks")
    op.drop_index("ix_tasks_created_at_desc", table_name="tasks")
    op.drop_index("ix_tasks_fulltext_search", table_name="tasks")
    op.drop_index("ix_tasks_instructions_gin", table_name="tasks")
    op.drop_index("ix_tasks_description_gin", table_name="tasks")
    op.drop_index("ix_tasks_title_gin", table_name="tasks")
    op.drop_index("ix_tasks_budget_range", table_name="tasks")
    op.drop_index("ix_tasks_task_type_platform", table_name="tasks")
    op.drop_index("ix_tasks_available", table_name="tasks")
    op.drop_index("ix_tasks_expires_at_not_null", table_name="tasks")
    op.drop_index("ix_tasks_creator_id_status", table_name="tasks")
    op.drop_index("ix_tasks_budget_created_at", table_name="tasks")
    op.drop_index("ix_tasks_platform_status", table_name="tasks")
