"""
Task Assignment Model.

Tracks the relationship between tasks and performers, managing the lifecycle
of task assignments from assignment through completion and verification.
"""

import logging
from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

logger = logging.getLogger(__name__)


class AssignmentStatusEnum(str, Enum):
    """Status values for task assignments."""

    ASSIGNED = "assigned"
    STARTED = "started"
    PROOF_SUBMITTED = "proof_submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskAssignment(BaseModel):
    """
    Task Assignment model tracking performer-task relationships.

    Manages the complete workflow from assignment through submission,
    verification, and final completion or rejection.
    """

    __tablename__ = "task_assignments"

    # Foreign keys
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the assigned task",
    )

    performer_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="ID of the performer (user)",
    )

    # Assignment status
    status: Mapped[AssignmentStatusEnum] = mapped_column(
        SQLEnum(AssignmentStatusEnum, name="assignment_status_enum", create_constraint=True),
        nullable=False,
        default=AssignmentStatusEnum.ASSIGNED,
        index=True,
        comment="Current assignment status",
    )

    # Lifecycle timestamps
    assigned_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when task was assigned",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when performer started the task",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when task was completed",
    )

    proof_submitted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when proof was submitted",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp when task was verified",
    )

    # Review and feedback
    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Rating given by task creator (1-5)",
    )

    review: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Review text from task creator",
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="assignments",
        lazy="selectin",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "(rating IS NULL) OR (rating >= 1 AND rating <= 5)",
            name="check_rating_range",
        ),
        # Unique constraint: one assignment per performer per task
        Index("idx_unique_task_performer", "task_id", "performer_id", unique=True),
        # Composite indexes for common queries
        Index("idx_assignment_performer_status", "performer_id", "status"),
        Index("idx_assignment_task_status", "task_id", "status"),
        Index("idx_assignment_assigned_at", "assigned_at"),
    )

    def __repr__(self) -> str:
        """String representation of TaskAssignment."""
        return (
            f"<TaskAssignment(id={self.id}, task_id={self.task_id}, "
            f"performer_id={self.performer_id}, status={self.status.value})>"
        )

    def mark_started(self) -> None:
        """
        Mark the assignment as started.

        Updates status and sets started_at timestamp.
        """
        if self.status != AssignmentStatusEnum.ASSIGNED:
            logger.warning(
                "Cannot mark assignment as started: invalid current status",
                extra={
                    "assignment_id": self.id,
                    "current_status": self.status.value,
                },
            )
            raise ValueError(
                f"Cannot mark assignment as started from status: {self.status.value}"
            )

        self.status = AssignmentStatusEnum.STARTED
        self.started_at = datetime.utcnow()

        logger.info(
            "Assignment marked as started",
            extra={
                "assignment_id": self.id,
                "task_id": self.task_id,
                "performer_id": self.performer_id,
            },
        )

    def submit_proof(self) -> None:
        """
        Mark proof as submitted.

        Updates status and sets proof_submitted_at timestamp.
        """
        if self.status not in [AssignmentStatusEnum.ASSIGNED, AssignmentStatusEnum.STARTED]:
            logger.warning(
                "Cannot submit proof: invalid current status",
                extra={
                    "assignment_id": self.id,
                    "current_status": self.status.value,
                },
            )
            raise ValueError(
                f"Cannot submit proof from status: {self.status.value}"
            )

        self.status = AssignmentStatusEnum.PROOF_SUBMITTED
        self.proof_submitted_at = datetime.utcnow()

        logger.info(
            "Proof submitted for assignment",
            extra={
                "assignment_id": self.id,
                "task_id": self.task_id,
                "performer_id": self.performer_id,
            },
        )

    def approve(self, rating: int | None = None, review: str | None = None) -> None:
        """
        Approve the assignment.

        Args:
            rating: Optional rating (1-5)
            review: Optional review text

        Raises:
            ValueError: If rating is out of valid range or current status is invalid
        """
        if self.status != AssignmentStatusEnum.PROOF_SUBMITTED:
            logger.warning(
                "Cannot approve assignment: invalid current status",
                extra={
                    "assignment_id": self.id,
                    "current_status": self.status.value,
                },
            )
            raise ValueError(
                f"Cannot approve assignment from status: {self.status.value}"
            )

        if rating is not None and (rating < 1 or rating > 5):
            logger.error(
                "Invalid rating value",
                extra={"assignment_id": self.id, "rating": rating},
            )
            raise ValueError("Rating must be between 1 and 5")

        self.status = AssignmentStatusEnum.APPROVED
        self.completed_at = datetime.utcnow()
        self.verified_at = datetime.utcnow()
        self.rating = rating
        self.review = review

        logger.info(
            "Assignment approved",
            extra={
                "assignment_id": self.id,
                "task_id": self.task_id,
                "performer_id": self.performer_id,
                "rating": rating,
            },
        )

    def reject(self, review: str | None = None) -> None:
        """
        Reject the assignment.

        Args:
            review: Optional rejection reason

        Raises:
            ValueError: If current status is invalid
        """
        if self.status != AssignmentStatusEnum.PROOF_SUBMITTED:
            logger.warning(
                "Cannot reject assignment: invalid current status",
                extra={
                    "assignment_id": self.id,
                    "current_status": self.status.value,
                },
            )
            raise ValueError(
                f"Cannot reject assignment from status: {self.status.value}"
            )

        self.status = AssignmentStatusEnum.REJECTED
        self.verified_at = datetime.utcnow()
        self.review = review

        logger.info(
            "Assignment rejected",
            extra={
                "assignment_id": self.id,
                "task_id": self.task_id,
                "performer_id": self.performer_id,
            },
        )

    def cancel(self) -> None:
        """
        Cancel the assignment.

        Can be cancelled from any non-terminal status.

        Raises:
            ValueError: If assignment is already in a terminal status
        """
        terminal_statuses = [
            AssignmentStatusEnum.APPROVED,
            AssignmentStatusEnum.COMPLETED,
            AssignmentStatusEnum.CANCELLED,
        ]

        if self.status in terminal_statuses:
            logger.warning(
                "Cannot cancel assignment: already in terminal status",
                extra={
                    "assignment_id": self.id,
                    "current_status": self.status.value,
                },
            )
            raise ValueError(
                f"Cannot cancel assignment from terminal status: {self.status.value}"
            )

        self.status = AssignmentStatusEnum.CANCELLED

        logger.info(
            "Assignment cancelled",
            extra={
                "assignment_id": self.id,
                "task_id": self.task_id,
                "performer_id": self.performer_id,
            },
        )
