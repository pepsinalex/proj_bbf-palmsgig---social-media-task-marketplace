"""
Task Management Routers.

This module exports all API routers for task management.
"""

from src.task_management.routers.tasks import router as tasks_router

__all__ = ["tasks_router"]
