"""
Task Model for Social Media Marketplace.

Defines the core Task model with comprehensive fields for social media tasks
including platform, type, budget, and lifecycle management.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import CheckConstraint, Enum as SQLEnum, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.models.base import BaseModel

logger = logging.getLogger(__name__)


class PlatformEnum(str, Enum):
    """Supported social media platforms."""

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"


class TaskTypeEnum(str, Enum):
    """Types of social media tasks."""

    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    FOLLOW = "follow"
    VIEW = "view"
    SUBSCRIBE = "subscribe"
    ENGAGEMENT = "engagement"


class TaskStatusEnum(str, Enum):
    """Task lifecycle statuses."""

    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Task(BaseModel):
    """
    Task model for social media marketplace tasks.

    Manages the complete lifecycle of tasks from creation to completion,
    including budget management, assignment tracking, and status transitions.
    """

    __tablename__ = "tasks"

    # Task identification and ownership
    creator_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="User ID of task creator"
    )

    # Task details
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Task title/summary"
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Detailed task description"
    )

    instructions: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Step-by-step instructions for performers"
    )

    # Platform and type
    platform: Mapped[PlatformEnum] = mapped_column(
        SQLEnum(PlatformEnum, name="platform_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Social media platform",
    )

    task_type: Mapped[TaskTypeEnum] = mapped_column(
        SQLEnum(TaskTypeEnum, name="task_type_enum", create_constraint=True),
        nullable=False,
        index=True,
        comment="Type of task",
    )

    # Financial details
    budget: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Budget per task completion (performer payment)",
    )

    service_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Platform service fee per task",
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total cost (budget + service_fee)",
    )

    # Task status and lifecycle
    status: Mapped[TaskStatusEnum] = mapped_column(
        SQLEnum(TaskStatusEnum, name="task_status_enum", create_constraint=True),
        nullable=False,
        default=TaskStatusEnum.DRAFT,
        index=True,
        comment="Current task status",
    )

    # Targeting criteria (JSON field for flexible targeting rules)
    target_criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON targeting criteria (location, demographics, etc.)",
    )

    # Performer management
    max_performers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Maximum number of performers allowed",
    )

    current_performers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of assigned performers",
    )

    # Timing
    expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True, index=True, comment="Task expiration timestamp"
    )

    # Relationships
    assignments: Mapped[list["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    history: Mapped[list["TaskHistory"]] = relationship(
        "TaskHistory",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TaskHistory.created_at.desc()",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint("budget > 0", name="check_budget_positive"),
        CheckConstraint("service_fee >= 0", name="check_service_fee_non_negative"),
        CheckConstraint("total_cost > 0", name="check_total_cost_positive"),
        CheckConstraint(
            "max_performers > 0", name="check_max_performers_positive"
        ),
        CheckConstraint(
            "current_performers >= 0", name="check_current_performers_non_negative"
        ),
        CheckConstraint(
            "current_performers <= max_performers",
            name="check_current_performers_within_max",
        ),
        # Composite indexes for common queries
        Index("idx_task_creator_status", "creator_id", "status"),
        Index("idx_task_platform_status", "platform", "status"),
        Index("idx_task_type_status", "task_type", "status"),
        Index("idx_task_status_expires", "status", "expires_at"),
        Index("idx_task_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of Task."""
        return (
            f"<Task(id={self.id}, title={self.title[:30]}, "
            f"status={self.status.value}, platform={self.platform.value})>"
        )

    def is_active(self) -> bool:
        """Check if task is in active status."""
        return self.status == TaskStatusEnum.ACTIVE

    def is_expired(self) -> bool:
        """Check if task has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def can_accept_performers(self) -> bool:
        """Check if task can accept more performers."""
        return (
            self.is_active()
            and not self.is_expired()
            and self.current_performers < self.max_performers
        )

    def increment_performers(self) -> None:
        """
        Increment current performer count.

        Raises:
            ValueError: If max performers limit reached
        """
        if self.current_performers >= self.max_performers:
            logger.error(
                "Cannot increment performers: max limit reached",
                extra={
                    "task_id": self.id,
                    "current_performers": self.current_performers,
                    "max_performers": self.max_performers,
                },
            )
            raise ValueError("Maximum performers limit reached")

        self.current_performers += 1
        logger.info(
            "Incremented task performers",
            extra={
                "task_id": self.id,
                "current_performers": self.current_performers,
                "max_performers": self.max_performers,
            },
        )

    def decrement_performers(self) -> None:
        """
        Decrement current performer count.

        Raises:
            ValueError: If current performers is already 0
        """
        if self.current_performers <= 0:
            logger.error(
                "Cannot decrement performers: already at zero",
                extra={"task_id": self.id, "current_performers": self.current_performers},
            )
            raise ValueError("Current performers already at zero")

        self.current_performers -= 1
        logger.info(
            "Decremented task performers",
            extra={
                "task_id": self.id,
                "current_performers": self.current_performers,
                "max_performers": self.max_performers,
            },
        )
