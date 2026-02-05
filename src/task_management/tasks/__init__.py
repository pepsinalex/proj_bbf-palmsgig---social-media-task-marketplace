"""
Background tasks for task management.

This module provides background task definitions for automated
task lifecycle management including expiration checks and cleanup.
"""

import logging

logger = logging.getLogger(__name__)

# Export task modules
from src.task_management.tasks.expiration_tasks import (  # noqa: F401
    cleanup_expired_assignments_task,
    check_expired_tasks_task,
    expire_incomplete_tasks_task,
    expire_unassigned_tasks_task,
)

__all__ = [
    "check_expired_tasks_task",
    "expire_unassigned_tasks_task",
    "expire_incomplete_tasks_task",
    "cleanup_expired_assignments_task",
]
