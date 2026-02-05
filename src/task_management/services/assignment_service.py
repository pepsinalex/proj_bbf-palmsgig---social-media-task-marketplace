"""
Task Assignment Service.

Manages task assignment logic with performer eligibility validation,
concurrent task limits, and assignment tracking.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum
from src/task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)

logger = logging.getLogger(__name__)

# Constants
MIN_RATING_FOR_ASSIGNMENT = 4.0
MAX_CONCURRENT_TASKS = 5


class AssignmentService:
    """
    Service for managing task assignments.

    Handles performer eligibility validation, concurrent task limits,
    and assignment operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize assignment service.

        Args:
            session: Database session for persistence
        """
        self.session = session

    async def validate_performer_eligibility(
        self, performer_id: str, task: Task
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if performer is eligible to accept a task.

        Args:
            performer_id: ID of the performer
            task: Task to validate for

        Returns:
            Tuple of (is_eligible, error_message)
        """
        # Check if task can accept more performers
        if not task.can_accept_performers():
            logger.warning(
                "Task cannot accept more performers",
                extra={
                    "task_id": task.id,
                    "performer_id": performer_id,
                    "current_performers": task.current_performers,
                    "max_performers": task.max_performers,
                    "status": task.status.value,
                },
            )
            return False, "Task is not accepting new performers"

        # Check if performer already assigned to this task
        existing_assignment = await self.session.scalar(
            select(TaskAssignment).where(
                and_(
                    TaskAssignment.task_id == task.id,
                    TaskAssignment.performer_id == performer_id,
                )
            )
        )

        if existing_assignment:
            logger.warning(
                "Performer already assigned to task",
                extra={
                    "task_id": task.id,
                    "performer_id": performer_id,
                    "assignment_id": existing_assignment.id,
                },
            )
            return False, "Already assigned to this task"

        # Check concurrent task limits
        concurrent_tasks = await self._count_concurrent_tasks(performer_id)
        if concurrent_tasks >= MAX_CONCURRENT_TASKS:
            logger.warning(
                "Performer has reached maximum concurrent tasks",
                extra={
                    "performer_id": performer_id,
                    "concurrent_tasks": concurrent_tasks,
                    "max_allowed": MAX_CONCURRENT_TASKS,
                },
            )
            return (
                False,
                f"Maximum concurrent tasks limit reached ({MAX_CONCURRENT_TASKS})",
            )

        # Check if performer has required social account for platform
        has_account = await self._check_social_account_exists(
            performer_id, task.platform
        )
        if not has_account:
            logger.warning(
                "Performer missing required social account",
                extra={
                    "performer_id": performer_id,
                    "required_platform": task.platform.value,
                    "task_id": task.id,
                },
            )
            return (
                False,
                f"No verified {task.platform.value} account connected",
            )

        # All validations passed
        logger.info(
            "Performer eligibility validated",
            extra={"performer_id": performer_id, "task_id": task.id},
        )
        return True, None

    async def check_concurrent_limits(
        self, performer_id: str
    ) -> tuple[int, int]:
        """
        Check performer's current concurrent task count against limits.

        Args:
            performer_id: ID of the performer

        Returns:
            Tuple of (current_count, max_allowed)
        """
        current_count = await self._count_concurrent_tasks(performer_id)
        return current_count, MAX_CONCURRENT_TASKS

    async def assign_task(
        self, task: Task, performer_id: str
    ) -> tuple[Optional[TaskAssignment], Optional[str]]:
        """
        Assign task to performer.

        Args:
            task: Task to assign
            performer_id: ID of the performer

        Returns:
            Tuple of (assignment, error_message)
        """
        # Validate eligibility
        is_eligible, error_msg = await self.validate_performer_eligibility(
            performer_id, task
        )
        if not is_eligible:
            return None, error_msg

        try:
            # Create assignment
            assignment = TaskAssignment(
                task_id=task.id,
                performer_id=performer_id,
                status=AssignmentStatusEnum.ASSIGNED,
                assigned_at=datetime.utcnow(),
            )

            # Increment task performer count
            task.increment_performers()

            # Save assignment
            self.session.add(assignment)
            await self.session.flush()

            logger.info(
                "Task assigned successfully",
                extra={
                    "task_id": task.id,
                    "performer_id": performer_id,
                    "assignment_id": assignment.id,
                    "current_performers": task.current_performers,
                },
            )

            return assignment, None

        except Exception as e:
            logger.error(
                "Failed to assign task",
                extra={
                    "task_id": task.id,
                    "performer_id": performer_id,
                    "error": str(e),
                },
            )
            return None, f"Assignment failed: {str(e)}"

    async def unassign_task(
        self, assignment: TaskAssignment
    ) -> tuple[bool, Optional[str]]:
        """
        Unassign task from performer.

        Args:
            assignment: Assignment to cancel

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Cancel assignment
            assignment.cancel()

            # Decrement task performer count
            task = await self.session.get(Task, assignment.task_id)
            if task:
                task.decrement_performers()
                logger.info(
                    "Task unassigned successfully",
                    extra={
                        "task_id": task.id,
                        "performer_id": assignment.performer_id,
                        "assignment_id": assignment.id,
                        "current_performers": task.current_performers,
                    },
                )
            else:
                logger.warning(
                    "Task not found during unassignment",
                    extra={"task_id": assignment.task_id},
                )

            return True, None

        except Exception as e:
            logger.error(
                "Failed to unassign task",
                extra={
                    "assignment_id": assignment.id,
                    "task_id": assignment.task_id,
                    "performer_id": assignment.performer_id,
                    "error": str(e),
                },
            )
            return False, f"Unassignment failed: {str(e)}"

    async def get_user_assignments(
        self,
        performer_id: str,
        status: Optional[AssignmentStatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskAssignment]:
        """
        Get assignments for a performer.

        Args:
            performer_id: ID of the performer
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of task assignments
        """
        query = select(TaskAssignment).where(
            TaskAssignment.performer_id == performer_id
        )

        if status:
            query = query.where(TaskAssignment.status == status)

        query = query.order_by(TaskAssignment.assigned_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        assignments = list(result.scalars().all())

        logger.info(
            "Retrieved user assignments",
            extra={
                "performer_id": performer_id,
                "status": status.value if status else None,
                "count": len(assignments),
                "limit": limit,
                "offset": offset,
            },
        )

        return assignments

    async def _count_concurrent_tasks(self, performer_id: str) -> int:
        """
        Count active concurrent tasks for performer.

        Args:
            performer_id: ID of the performer

        Returns:
            Number of active concurrent tasks
        """
        # Count assignments that are not in terminal states
        active_statuses = [
            AssignmentStatusEnum.ASSIGNED,
            AssignmentStatusEnum.STARTED,
            AssignmentStatusEnum.PROOF_SUBMITTED,
            AssignmentStatusEnum.IN_REVIEW,
        ]

        query = select(func.count()).select_from(TaskAssignment).where(
            and_(
                TaskAssignment.performer_id == performer_id,
                TaskAssignment.status.in_(active_statuses),
            )
        )

        result = await self.session.execute(query)
        count = result.scalar() or 0

        logger.debug(
            "Counted concurrent tasks",
            extra={"performer_id": performer_id, "count": count},
        )

        return count

    async def _check_social_account_exists(
        self, user_id: str, platform: PlatformEnum
    ) -> bool:
        """
        Check if user has a verified social account for the platform.

        Args:
            user_id: ID of the user
            platform: Social media platform

        Returns:
            True if account exists and is verified
        """
        # Import here to avoid circular dependency
        from sqlalchemy import select

        try:
            # Query for social account
            # Using dynamic import to avoid circular dependency
            from src.social_media.models.social_account import SocialAccount

            query = select(SocialAccount).where(
                and_(
                    SocialAccount.user_id == user_id,
                    SocialAccount.platform == platform.value,
                    SocialAccount.is_verified == True,  # noqa: E712
                )
            )

            result = await self.session.execute(query)
            account = result.scalar_one_or_none()

            has_account = account is not None
            logger.debug(
                "Checked social account existence",
                extra={
                    "user_id": user_id,
                    "platform": platform.value,
                    "has_account": has_account,
                },
            )

            return has_account

        except Exception as e:
            logger.error(
                "Error checking social account",
                extra={
                    "user_id": user_id,
                    "platform": platform.value,
                    "error": str(e),
                },
            )
            # Return False to be safe - deny assignment if we can't verify
            return False
