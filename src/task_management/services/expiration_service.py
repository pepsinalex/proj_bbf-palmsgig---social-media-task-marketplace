"""
Task Expiration and Cleanup Service.

Manages automatic expiration of tasks and cleanup of expired assignments.
Includes configurable expiration times and automated cleanup logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import TaskStatusEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)

logger = logging.getLogger(__name__)

# Configurable expiration times (in hours)
ASSIGNMENT_EXPIRATION_HOURS = 24
COMPLETION_EXPIRATION_HOURS = 48


class ExpirationService:
    """
    Service for managing task and assignment expiration.

    Handles automatic expiration checks and cleanup operations for tasks
    and assignments that have exceeded their time limits.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize expiration service.

        Args:
            session: Database session for persistence
        """
        self.session = session

    async def check_expired_tasks(self) -> list[Task]:
        """
        Check for expired tasks and return them.

        Returns:
            List of expired tasks that need attention
        """
        now = datetime.utcnow()

        # Query for active tasks that have passed their expiration date
        query = select(Task).where(
            and_(
                Task.status == TaskStatusEnum.ACTIVE,
                Task.expires_at.isnot(None),
                Task.expires_at <= now,
            )
        )

        result = await self.session.execute(query)
        expired_tasks = list(result.scalars().all())

        logger.info(
            "Checked for expired tasks",
            extra={
                "count": len(expired_tasks),
                "check_time": now.isoformat(),
            },
        )

        return expired_tasks

    async def expire_unassigned_tasks(
        self, max_age_days: Optional[int] = 30
    ) -> int:
        """
        Expire tasks that have been unassigned for too long.

        Args:
            max_age_days: Maximum age in days before expiration (default: 30)

        Returns:
            Number of tasks expired
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        # Find active tasks with no performers that are too old
        query = select(Task).where(
            and_(
                Task.status == TaskStatusEnum.ACTIVE,
                Task.current_performers == 0,
                Task.created_at <= cutoff_date,
            )
        )

        result = await self.session.execute(query)
        tasks_to_expire = list(result.scalars().all())

        expired_count = 0
        for task in tasks_to_expire:
            try:
                # Use state machine for proper transition
                from src.task_management.services.state_machine import (
                    TaskStateMachine,
                )

                state_machine = TaskStateMachine(self.session)
                await state_machine.transition_task(
                    task=task,
                    new_status=TaskStatusEnum.EXPIRED,
                    changed_by="system",
                    reason=f"Task expired: no assignments after {max_age_days} days",
                )
                expired_count += 1

                logger.info(
                    "Expired unassigned task",
                    extra={
                        "task_id": task.id,
                        "created_at": task.created_at.isoformat(),
                        "age_days": (datetime.utcnow() - task.created_at).days,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to expire task",
                    extra={
                        "task_id": task.id,
                        "error": str(e),
                    },
                )

        logger.info(
            "Expired unassigned tasks",
            extra={
                "expired_count": expired_count,
                "max_age_days": max_age_days,
                "cutoff_date": cutoff_date.isoformat(),
            },
        )

        return expired_count

    async def expire_incomplete_tasks(
        self, completion_hours: Optional[int] = None
    ) -> int:
        """
        Expire tasks with incomplete assignments after time limit.

        Args:
            completion_hours: Hours allowed for completion (default: COMPLETION_EXPIRATION_HOURS)

        Returns:
            Number of tasks expired
        """
        if completion_hours is None:
            completion_hours = COMPLETION_EXPIRATION_HOURS

        cutoff_date = datetime.utcnow() - timedelta(hours=completion_hours)

        # Find active tasks where all assignments are old and not completed
        query = select(Task).where(
            and_(
                Task.status == TaskStatusEnum.ACTIVE,
                Task.current_performers > 0,
                Task.current_performers < Task.max_performers,
                Task.created_at <= cutoff_date,
            )
        )

        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        expired_count = 0
        for task in tasks:
            # Check if all assignments are stale
            has_recent_activity = await self._has_recent_assignment_activity(
                task.id, hours=completion_hours
            )

            if not has_recent_activity:
                try:
                    # Expire task
                    from src.task_management.services.state_machine import (
                        TaskStateMachine,
                    )

                    state_machine = TaskStateMachine(self.session)
                    await state_machine.transition_task(
                        task=task,
                        new_status=TaskStatusEnum.EXPIRED,
                        changed_by="system",
                        reason=f"Task expired: incomplete after {completion_hours} hours",
                    )
                    expired_count += 1

                    logger.info(
                        "Expired incomplete task",
                        extra={
                            "task_id": task.id,
                            "current_performers": task.current_performers,
                            "max_performers": task.max_performers,
                            "hours_since_creation": (
                                datetime.utcnow() - task.created_at
                            ).total_seconds()
                            / 3600,
                        },
                    )

                except Exception as e:
                    logger.error(
                        "Failed to expire incomplete task",
                        extra={
                            "task_id": task.id,
                            "error": str(e),
                        },
                    )

        logger.info(
            "Expired incomplete tasks",
            extra={
                "expired_count": expired_count,
                "completion_hours": completion_hours,
                "cutoff_date": cutoff_date.isoformat(),
            },
        )

        return expired_count

    async def cleanup_expired_assignments(
        self, assignment_hours: Optional[int] = None
    ) -> int:
        """
        Clean up assignments that have been pending too long.

        Args:
            assignment_hours: Hours before assignment expires (default: ASSIGNMENT_EXPIRATION_HOURS)

        Returns:
            Number of assignments cleaned up
        """
        if assignment_hours is None:
            assignment_hours = ASSIGNMENT_EXPIRATION_HOURS

        cutoff_date = datetime.utcnow() - timedelta(hours=assignment_hours)

        # Find assignments that are assigned but not started for too long
        query = select(TaskAssignment).where(
            and_(
                TaskAssignment.status == AssignmentStatusEnum.ASSIGNED,
                TaskAssignment.assigned_at <= cutoff_date,
            )
        )

        result = await self.session.execute(query)
        stale_assignments = list(result.scalars().all())

        cleaned_count = 0
        for assignment in stale_assignments:
            try:
                # Cancel the assignment
                assignment.cancel()

                # Decrement task performer count
                task = await self.session.get(Task, assignment.task_id)
                if task and task.current_performers > 0:
                    task.decrement_performers()

                cleaned_count += 1

                logger.info(
                    "Cleaned up expired assignment",
                    extra={
                        "assignment_id": assignment.id,
                        "task_id": assignment.task_id,
                        "performer_id": assignment.performer_id,
                        "assigned_at": assignment.assigned_at.isoformat(),
                        "hours_since_assignment": (
                            datetime.utcnow() - assignment.assigned_at
                        ).total_seconds()
                        / 3600,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to cleanup assignment",
                    extra={
                        "assignment_id": assignment.id,
                        "error": str(e),
                    },
                )

        logger.info(
            "Cleaned up expired assignments",
            extra={
                "cleaned_count": cleaned_count,
                "assignment_hours": assignment_hours,
                "cutoff_date": cutoff_date.isoformat(),
            },
        )

        return cleaned_count

    async def _has_recent_assignment_activity(
        self, task_id: str, hours: int
    ) -> bool:
        """
        Check if task has recent assignment activity.

        Args:
            task_id: ID of the task
            hours: Number of hours to look back

        Returns:
            True if there has been recent activity
        """
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)

        # Check for recent assignments or status updates
        query = select(TaskAssignment).where(
            and_(
                TaskAssignment.task_id == task_id,
                TaskAssignment.assigned_at >= cutoff_date,
            )
        )

        result = await self.session.execute(query)
        has_activity = result.scalar_one_or_none() is not None

        logger.debug(
            "Checked for recent assignment activity",
            extra={
                "task_id": task_id,
                "hours": hours,
                "has_activity": has_activity,
            },
        )

        return has_activity
