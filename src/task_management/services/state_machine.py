"""
Task State Machine Service.

Manages task status transitions with validation and automation logic.
Ensures all state transitions follow business rules and maintains data integrity.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import TaskStatusEnum
from src/task_management.models.task import Task
from src.task_management.models.task_history import TaskHistory

logger = logging.getLogger(__name__)


class TaskStateMachine:
    """
    State machine for managing task status transitions.

    Validates transitions, enforces business rules, and maintains audit trail
    through task history entries.
    """

    # Define valid state transitions
    STATE_TRANSITIONS = {
        TaskStatusEnum.DRAFT: {
            TaskStatusEnum.PENDING_PAYMENT,
            TaskStatusEnum.CANCELLED,
        },
        TaskStatusEnum.PENDING_PAYMENT: {
            TaskStatusEnum.ACTIVE,
            TaskStatusEnum.CANCELLED,
        },
        TaskStatusEnum.ACTIVE: {
            TaskStatusEnum.PAUSED,
            TaskStatusEnum.COMPLETED,
            TaskStatusEnum.CANCELLED,
            TaskStatusEnum.EXPIRED,
        },
        TaskStatusEnum.PAUSED: {
            TaskStatusEnum.ACTIVE,
            TaskStatusEnum.CANCELLED,
            TaskStatusEnum.EXPIRED,
        },
        TaskStatusEnum.COMPLETED: set(),
        TaskStatusEnum.CANCELLED: set(),
        TaskStatusEnum.EXPIRED: set(),
    }

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize state machine.

        Args:
            session: Database session for persistence
        """
        self.session = session

    def validate_transition(
        self, current_status: TaskStatusEnum, new_status: TaskStatusEnum
    ) -> bool:
        """
        Validate if a status transition is allowed.

        Args:
            current_status: Current task status
            new_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = self.STATE_TRANSITIONS.get(current_status, set())
        is_valid = new_status in valid_transitions

        if not is_valid:
            logger.warning(
                "Invalid state transition attempted",
                extra={
                    "current_status": current_status.value,
                    "new_status": new_status.value,
                    "valid_transitions": [s.value for s in valid_transitions],
                },
            )

        return is_valid

    def can_transition(
        self, current_status: TaskStatusEnum, new_status: TaskStatusEnum
    ) -> bool:
        """
        Check if transition is possible (alias for validate_transition).

        Args:
            current_status: Current task status
            new_status: Desired new status

        Returns:
            True if transition is valid, False otherwise
        """
        return self.validate_transition(current_status, new_status)

    def get_valid_transitions(
        self, current_status: TaskStatusEnum
    ) -> set[TaskStatusEnum]:
        """
        Get all valid transitions from current status.

        Args:
            current_status: Current task status

        Returns:
            Set of valid target statuses
        """
        return self.STATE_TRANSITIONS.get(current_status, set())

    async def transition_task(
        self,
        task: Task,
        new_status: TaskStatusEnum,
        changed_by: str,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Transition task to new status with validation and history tracking.

        Args:
            task: Task to transition
            new_status: Target status
            changed_by: User ID making the change
            reason: Optional reason for transition
            metadata: Optional additional metadata

        Returns:
            True if transition successful, False otherwise

        Raises:
            ValueError: If transition is invalid
        """
        previous_status = task.status

        # Validate transition
        if not self.validate_transition(previous_status, new_status):
            error_msg = (
                f"Invalid transition from {previous_status.value} to {new_status.value}"
            )
            logger.error(
                "State transition validation failed",
                extra={
                    "task_id": task.id,
                    "previous_status": previous_status.value,
                    "new_status": new_status.value,
                    "changed_by": changed_by,
                },
            )
            raise ValueError(error_msg)

        # Apply automatic transition logic
        await self._apply_transition_logic(task, new_status)

        # Update task status
        task.status = new_status

        # Create history entry
        history_entry = TaskHistory.create_entry(
            task_id=task.id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata or {},
        )

        self.session.add(history_entry)

        logger.info(
            "Task status transitioned successfully",
            extra={
                "task_id": task.id,
                "previous_status": previous_status.value,
                "new_status": new_status.value,
                "changed_by": changed_by,
            },
        )

        return True

    async def _apply_transition_logic(
        self, task: Task, new_status: TaskStatusEnum
    ) -> None:
        """
        Apply automatic logic based on state transition.

        Args:
            task: Task being transitioned
            new_status: Target status
        """
        # Set expires_at when transitioning to active
        if new_status == TaskStatusEnum.ACTIVE and task.expires_at is None:
            # Default expiration: 7 days from now
            from datetime import timedelta

            task.expires_at = datetime.utcnow() + timedelta(days=7)
            logger.info(
                "Set default expiration for active task",
                extra={
                    "task_id": task.id,
                    "expires_at": task.expires_at.isoformat(),
                },
            )

        # Clear expires_at when pausing or completing
        if new_status in [TaskStatusEnum.PAUSED, TaskStatusEnum.COMPLETED]:
            if task.expires_at is not None:
                logger.info(
                    "Cleared expiration timestamp",
                    extra={
                        "task_id": task.id,
                        "new_status": new_status.value,
                    },
                )
                task.expires_at = None

        # Handle completion status
        if new_status == TaskStatusEnum.COMPLETED:
            logger.info(
                "Task marked as completed",
                extra={
                    "task_id": task.id,
                    "current_performers": task.current_performers,
                    "max_performers": task.max_performers,
                },
            )

        # Handle expiration
        if new_status == TaskStatusEnum.EXPIRED:
            logger.info(
                "Task marked as expired",
                extra={
                    "task_id": task.id,
                    "current_performers": task.current_performers,
                    "max_performers": task.max_performers,
                },
            )

        # Handle cancellation
        if new_status == TaskStatusEnum.CANCELLED:
            logger.info(
                "Task cancelled",
                extra={
                    "task_id": task.id,
                    "previous_status": task.status.value,
                },
            )
