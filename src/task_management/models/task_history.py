"""
Task History Model.

Provides an immutable audit trail of all task status changes, tracking what changed,
when it changed, who made the change, and why.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import Base

logger = logging.getLogger(__name__)


class TaskHistory(Base):
    """
    Task History model for audit trail.

    Provides an immutable record of all task state transitions with
    full context about who made the change and why.
    """

    __tablename__ = "task_history"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        comment="Unique history entry ID",
    )

    # Foreign key to task
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the task that was changed",
    )

    # Status transition
    previous_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Task status before the change",
    )

    new_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Task status after the change",
    )

    # Change metadata
    changed_by: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="User ID who made the change",
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reason/description for the change",
    )

    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional JSON metadata about the change",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when the change occurred",
    )

    # Relationship
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="history",
        lazy="selectin",
    )

    # Table constraints
    __table_args__ = (
        # Composite indexes for audit queries
        Index("idx_history_task_created", "task_id", "created_at"),
        Index("idx_history_changed_by_created", "changed_by", "created_at"),
        Index("idx_history_new_status_created", "new_status", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of TaskHistory."""
        return (
            f"<TaskHistory(id={self.id}, task_id={self.task_id}, "
            f"{self.previous_status} -> {self.new_status})>"
        )

    @classmethod
    def create_entry(
        cls,
        task_id: str,
        previous_status: str,
        new_status: str,
        changed_by: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "TaskHistory":
        """
        Create a new history entry.

        Args:
            task_id: ID of the task
            previous_status: Previous task status
            new_status: New task status
            changed_by: User ID who made the change
            reason: Optional reason for the change
            metadata: Optional additional metadata

        Returns:
            New TaskHistory instance

        Example:
            >>> history = TaskHistory.create_entry(
            ...     task_id="task-123",
            ...     previous_status="draft",
            ...     new_status="active",
            ...     changed_by="user-456",
            ...     reason="Task published by creator",
            ...     metadata={"ip_address": "192.168.1.1"}
            ... )
        """
        import uuid

        entry = cls(
            id=str(uuid.uuid4()),
            task_id=task_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )

        logger.info(
            "Task history entry created",
            extra={
                "history_id": entry.id,
                "task_id": task_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "changed_by": changed_by,
            },
        )

        return entry

    def to_dict(self) -> dict[str, Any]:
        """
        Convert history entry to dictionary.

        Returns:
            Dictionary representation of the history entry
        """
        return {
            "id": self.id,
            "task_id": self.task_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
