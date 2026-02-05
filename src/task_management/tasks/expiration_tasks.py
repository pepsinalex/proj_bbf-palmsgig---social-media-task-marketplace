"""
Expiration Background Tasks.

Provides background tasks for checking and processing task expirations
and assignment cleanup.
"""

import logging
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database import get_db_session
from src.task_management.services.expiration_service import ExpirationService
from src.task_management.services.state_machine import TaskStateMachine

logger = logging.getLogger(__name__)


async def check_expired_tasks_task() -> Dict[str, int]:
    """
    Background task to check and expire tasks that have passed their expiration date.

    Returns:
        Dictionary with count of expired tasks
    """
    logger.info("Starting check_expired_tasks background task")

    try:
        # Get database session
        async for session in get_db_session():
            expiration_service = ExpirationService(session)
            state_machine = TaskStateMachine(session)

            # Get expired tasks
            expired_tasks = await expiration_service.check_expired_tasks()

            # Transition each task to expired status
            expired_count = 0
            for task in expired_tasks:
                try:
                    await state_machine.transition_task(
                        task=task,
                        new_status=task.status.__class__.EXPIRED,
                        changed_by="system",
                        reason="Task expired based on expiration date",
                    )
                    expired_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to expire task",
                        extra={"task_id": task.id, "error": str(e)},
                    )

            # Commit changes
            await session.commit()

            logger.info(
                "check_expired_tasks task completed",
                extra={"expired_count": expired_count},
            )

            return {"expired_count": expired_count}

    except Exception as e:
        logger.error(
            "check_expired_tasks task failed",
            extra={"error": str(e)},
        )
        raise


async def expire_unassigned_tasks_task(max_age_days: int = 30) -> Dict[str, int]:
    """
    Background task to expire tasks that have been unassigned for too long.

    Args:
        max_age_days: Maximum age in days before expiration

    Returns:
        Dictionary with count of expired tasks
    """
    logger.info(
        "Starting expire_unassigned_tasks background task",
        extra={"max_age_days": max_age_days},
    )

    try:
        # Get database session
        async for session in get_db_session():
            expiration_service = ExpirationService(session)

            # Expire unassigned tasks
            expired_count = await expiration_service.expire_unassigned_tasks(
                max_age_days=max_age_days
            )

            # Commit changes
            await session.commit()

            logger.info(
                "expire_unassigned_tasks task completed",
                extra={
                    "expired_count": expired_count,
                    "max_age_days": max_age_days,
                },
            )

            return {"expired_count": expired_count}

    except Exception as e:
        logger.error(
            "expire_unassigned_tasks task failed",
            extra={"error": str(e), "max_age_days": max_age_days},
        )
        raise


async def expire_incomplete_tasks_task(
    completion_hours: int = 48,
) -> Dict[str, int]:
    """
    Background task to expire tasks with incomplete assignments after time limit.

    Args:
        completion_hours: Hours allowed for completion

    Returns:
        Dictionary with count of expired tasks
    """
    logger.info(
        "Starting expire_incomplete_tasks background task",
        extra={"completion_hours": completion_hours},
    )

    try:
        # Get database session
        async for session in get_db_session():
            expiration_service = ExpirationService(session)

            # Expire incomplete tasks
            expired_count = await expiration_service.expire_incomplete_tasks(
                completion_hours=completion_hours
            )

            # Commit changes
            await session.commit()

            logger.info(
                "expire_incomplete_tasks task completed",
                extra={
                    "expired_count": expired_count,
                    "completion_hours": completion_hours,
                },
            )

            return {"expired_count": expired_count}

    except Exception as e:
        logger.error(
            "expire_incomplete_tasks task failed",
            extra={"error": str(e), "completion_hours": completion_hours},
        )
        raise


async def cleanup_expired_assignments_task(
    assignment_hours: int = 24,
) -> Dict[str, int]:
    """
    Background task to clean up assignments that have been pending too long.

    Args:
        assignment_hours: Hours before assignment expires

    Returns:
        Dictionary with count of cleaned up assignments
    """
    logger.info(
        "Starting cleanup_expired_assignments background task",
        extra={"assignment_hours": assignment_hours},
    )

    try:
        # Get database session
        async for session in get_db_session():
            expiration_service = ExpirationService(session)

            # Cleanup expired assignments
            cleaned_count = await expiration_service.cleanup_expired_assignments(
                assignment_hours=assignment_hours
            )

            # Commit changes
            await session.commit()

            logger.info(
                "cleanup_expired_assignments task completed",
                extra={
                    "cleaned_count": cleaned_count,
                    "assignment_hours": assignment_hours,
                },
            )

            return {"cleaned_count": cleaned_count}

    except Exception as e:
        logger.error(
            "cleanup_expired_assignments task failed",
            extra={"error": str(e), "assignment_hours": assignment_hours},
        )
        raise
