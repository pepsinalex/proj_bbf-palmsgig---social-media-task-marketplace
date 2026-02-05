"""
Task Discovery Service with Advanced Filtering and Pagination.

Provides comprehensive task discovery functionality with database queries,
filtering, pagination, and integration with search service.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.schemas.discovery import (
    PaginationParams,
    TaskDiscoveryResponse,
    TaskFilter,
    TaskSearch,
)

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Service for task discovery with filtering, search, and pagination.

    Handles database queries for task discovery with comprehensive filtering
    options, sorting, and pagination support.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize DiscoveryService with database session.

        Args:
            db_session: Active async database session
        """
        self.db_session = db_session
        logger.info("DiscoveryService initialized")

    async def get_available_tasks(
        self,
        filters: TaskFilter,
        pagination: PaginationParams,
    ) -> tuple[list[TaskDiscoveryResponse], int]:
        """
        Get available tasks with filtering and pagination.

        Args:
            filters: Filter parameters for task discovery
            pagination: Pagination parameters

        Returns:
            Tuple of (task_list, total_count)

        Raises:
            Exception: If task retrieval fails
        """
        try:
            logger.info(
                "Fetching available tasks",
                extra={
                    "filters": filters.model_dump(exclude_none=True),
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                },
            )

            # Build base query
            query = select(Task)

            # Apply filters
            query = self._apply_filters(query, filters)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db_session.execute(count_query)
            total_count = count_result.scalar_one()

            # Apply sorting
            query = self._apply_sorting(query, filters.sort_by, filters.sort_order)

            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db_session.execute(query)
            tasks = result.scalars().all()

            # Convert to response models
            task_responses = [
                TaskDiscoveryResponse(
                    id=task.id,
                    title=task.title,
                    description=task.description,
                    instructions=task.instructions,
                    platform=task.platform,
                    task_type=task.task_type,
                    budget=task.budget,
                    service_fee=task.service_fee,
                    total_cost=task.total_cost,
                    max_performers=task.max_performers,
                    current_performers=task.current_performers,
                    status=task.status,
                    creator_id=task.creator_id,
                    target_criteria=task.target_criteria,
                    expires_at=task.expires_at,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                )
                for task in tasks
            ]

            logger.info(
                "Available tasks retrieved successfully",
                extra={
                    "total_count": total_count,
                    "returned_count": len(task_responses),
                    "page": pagination.page,
                },
            )

            return task_responses, total_count

        except Exception as e:
            logger.error(
                "Failed to retrieve available tasks",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "filters": filters.model_dump(exclude_none=True),
                },
            )
            raise

    async def search_tasks(
        self,
        search_params: TaskSearch,
        filters: TaskFilter,
        pagination: PaginationParams,
    ) -> tuple[list[TaskDiscoveryResponse], int]:
        """
        Search tasks with full-text search and filtering.

        Note: This provides database-level search. For Elasticsearch integration,
        use SearchService directly.

        Args:
            search_params: Search parameters
            filters: Additional filter parameters
            pagination: Pagination parameters

        Returns:
            Tuple of (task_list, total_count)

        Raises:
            Exception: If search fails
        """
        try:
            logger.info(
                "Searching tasks",
                extra={
                    "query": search_params.query,
                    "search_fields": search_params.search_fields,
                    "page": pagination.page,
                },
            )

            # Build base query with text search
            query = select(Task)

            # Apply text search across specified fields
            search_conditions = []
            search_query = f"%{search_params.query}%"

            if "title" in search_params.search_fields:
                search_conditions.append(Task.title.ilike(search_query))
            if "description" in search_params.search_fields:
                search_conditions.append(Task.description.ilike(search_query))
            if "instructions" in search_params.search_fields:
                search_conditions.append(Task.instructions.ilike(search_query))

            if search_conditions:
                query = query.where(or_(*search_conditions))

            # Apply additional filters
            query = self._apply_filters(query, filters)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db_session.execute(count_query)
            total_count = count_result.scalar_one()

            # Apply sorting
            query = self._apply_sorting(query, filters.sort_by, filters.sort_order)

            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db_session.execute(query)
            tasks = result.scalars().all()

            # Convert to response models
            task_responses = [
                TaskDiscoveryResponse(
                    id=task.id,
                    title=task.title,
                    description=task.description,
                    instructions=task.instructions,
                    platform=task.platform,
                    task_type=task.task_type,
                    budget=task.budget,
                    service_fee=task.service_fee,
                    total_cost=task.total_cost,
                    max_performers=task.max_performers,
                    current_performers=task.current_performers,
                    status=task.status,
                    creator_id=task.creator_id,
                    target_criteria=task.target_criteria,
                    expires_at=task.expires_at,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                )
                for task in tasks
            ]

            logger.info(
                "Task search completed successfully",
                extra={
                    "query": search_params.query,
                    "total_count": total_count,
                    "returned_count": len(task_responses),
                },
            )

            return task_responses, total_count

        except Exception as e:
            logger.error(
                "Failed to search tasks",
                extra={
                    "query": search_params.query,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _apply_filters(self, query: Any, filters: TaskFilter) -> Any:
        """
        Apply filters to query.

        Args:
            query: SQLAlchemy query object
            filters: Filter parameters

        Returns:
            Modified query with filters applied
        """
        conditions = []

        # Platform filter
        if filters.platform is not None:
            conditions.append(Task.platform == filters.platform)

        # Task type filter
        if filters.task_type is not None:
            conditions.append(Task.task_type == filters.task_type)

        # Status filter (default to ACTIVE if not specified)
        if filters.status is not None:
            conditions.append(Task.status == filters.status)
        else:
            conditions.append(Task.status == TaskStatusEnum.ACTIVE)

        # Budget range filters
        if filters.min_budget is not None:
            conditions.append(Task.budget >= filters.min_budget)

        if filters.max_budget is not None:
            conditions.append(Task.budget <= filters.max_budget)

        # Creator filter
        if filters.creator_id is not None:
            conditions.append(Task.creator_id == filters.creator_id)

        # Exclude expired tasks
        if filters.exclude_expired:
            conditions.append(
                or_(Task.expires_at.is_(None), Task.expires_at > datetime.utcnow())
            )

        # Exclude full tasks
        if filters.exclude_full:
            conditions.append(Task.current_performers < Task.max_performers)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_sorting(self, query: Any, sort_by: str, sort_order: str) -> Any:
        """
        Apply sorting to query.

        Args:
            query: SQLAlchemy query object
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Modified query with sorting applied
        """
        sort_field_map = {
            "created_at": Task.created_at,
            "budget": Task.budget,
            "expires_at": Task.expires_at,
            "current_performers": Task.current_performers,
        }

        sort_field = sort_field_map.get(sort_by, Task.created_at)

        if sort_order.lower() == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        return query

    async def get_task_by_id(self, task_id: str) -> TaskDiscoveryResponse | None:
        """
        Get a single task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task discovery response or None if not found

        Raises:
            Exception: If task retrieval fails
        """
        try:
            query = select(Task).where(Task.id == task_id)
            result = await self.db_session.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                logger.info("Task not found", extra={"task_id": task_id})
                return None

            task_response = TaskDiscoveryResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                instructions=task.instructions,
                platform=task.platform,
                task_type=task.task_type,
                budget=task.budget,
                service_fee=task.service_fee,
                total_cost=task.total_cost,
                max_performers=task.max_performers,
                current_performers=task.current_performers,
                status=task.status,
                creator_id=task.creator_id,
                target_criteria=task.target_criteria,
                expires_at=task.expires_at,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )

            logger.info("Task retrieved successfully", extra={"task_id": task_id})

            return task_response

        except Exception as e:
            logger.error(
                "Failed to retrieve task",
                extra={
                    "task_id": task_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def get_task_count_by_filters(self, filters: TaskFilter) -> int:
        """
        Get count of tasks matching filters.

        Args:
            filters: Filter parameters

        Returns:
            Total count of matching tasks

        Raises:
            Exception: If count retrieval fails
        """
        try:
            query = select(func.count(Task.id))
            query = self._apply_filters(query, filters)

            result = await self.db_session.execute(query)
            count = result.scalar_one()

            logger.info(
                "Task count retrieved",
                extra={
                    "count": count,
                    "filters": filters.model_dump(exclude_none=True),
                },
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get task count",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "filters": filters.model_dump(exclude_none=True),
                },
            )
            raise
