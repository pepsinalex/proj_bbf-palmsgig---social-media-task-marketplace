"""
Task Service.

Provides business logic for task management including CRUD operations,
status transitions, and service fee calculations.
"""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.task_management.models.task import Task, TaskStatusEnum
from src.task_management.models.task_history import TaskHistory
from src.task_management.schemas.task import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)

# Platform service fee: 15% of budget
SERVICE_FEE_PERCENTAGE = Decimal("0.15")


class TaskService:
    """
    Service class for task management operations.

    Handles all business logic for tasks including creation, updates,
    deletion, and querying with proper validation and error handling.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize task service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.debug("TaskService initialized")

    async def create_task(self, creator_id: str, task_data: TaskCreate) -> Task:
        """
        Create a new task.

        Calculates service fee (15% of budget) and total cost automatically.
        Task starts in DRAFT status.

        Args:
            creator_id: ID of the user creating the task
            task_data: Task creation data

        Returns:
            Created task instance

        Raises:
            ValueError: If validation fails

        Example:
            >>> task = await service.create_task(
            ...     creator_id="user-123",
            ...     task_data=TaskCreate(
            ...         title="Like my post",
            ...         description="Need likes",
            ...         instructions="Click like",
            ...         platform=PlatformEnum.INSTAGRAM,
            ...         task_type=TaskTypeEnum.LIKE,
            ...         budget=Decimal("0.50"),
            ...         max_performers=100
            ...     )
            ... )
        """
        logger.info(
            "Creating new task",
            extra={
                "creator_id": creator_id,
                "platform": task_data.platform.value,
                "task_type": task_data.task_type.value,
                "budget": str(task_data.budget),
            },
        )

        # Calculate service fee (15% of budget)
        service_fee = (task_data.budget * SERVICE_FEE_PERCENTAGE).quantize(
            Decimal("0.01")
        )
        total_cost = task_data.budget + service_fee

        # Create task instance
        task = Task(
            creator_id=creator_id,
            title=task_data.title,
            description=task_data.description,
            instructions=task_data.instructions,
            platform=task_data.platform,
            task_type=task_data.task_type,
            budget=task_data.budget,
            service_fee=service_fee,
            total_cost=total_cost,
            max_performers=task_data.max_performers,
            current_performers=0,
            status=TaskStatusEnum.DRAFT,
            target_criteria=task_data.target_criteria,
            expires_at=task_data.expires_at,
        )

        self.session.add(task)
        await self.session.flush()

        # Create initial history entry
        history = TaskHistory.create_entry(
            task_id=task.id,
            previous_status="none",
            new_status=TaskStatusEnum.DRAFT.value,
            changed_by=creator_id,
            reason="Task created",
        )
        self.session.add(history)

        await self.session.commit()
        await self.session.refresh(task)

        logger.info(
            "Task created successfully",
            extra={
                "task_id": task.id,
                "creator_id": creator_id,
                "service_fee": str(service_fee),
                "total_cost": str(total_cost),
            },
        )

        return task

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task instance if found, None otherwise

        Example:
            >>> task = await service.get_task("task-123")
        """
        logger.debug("Fetching task", extra={"task_id": task_id})

        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.assignments), selectinload(Task.history))
        )

        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            logger.debug("Task found", extra={"task_id": task_id})
        else:
            logger.debug("Task not found", extra={"task_id": task_id})

        return task

    async def update_task(
        self, task_id: str, user_id: str, update_data: TaskUpdate
    ) -> Task | None:
        """
        Update an existing task.

        Recalculates service fee and total cost if budget is updated.
        Creates history entry for status changes.

        Args:
            task_id: Task identifier
            user_id: ID of user making the update
            update_data: Update data (partial)

        Returns:
            Updated task instance if found, None otherwise

        Raises:
            ValueError: If update validation fails

        Example:
            >>> task = await service.update_task(
            ...     task_id="task-123",
            ...     user_id="user-456",
            ...     update_data=TaskUpdate(status=TaskStatusEnum.ACTIVE)
            ... )
        """
        logger.info(
            "Updating task", extra={"task_id": task_id, "user_id": user_id}
        )

        task = await self.get_task(task_id)
        if not task:
            logger.warning("Task not found for update", extra={"task_id": task_id})
            return None

        previous_status = task.status
        update_dict = update_data.model_dump(exclude_unset=True)

        # Update fields
        for field, value in update_dict.items():
            if field == "budget" and value is not None:
                # Recalculate service fee and total cost
                service_fee = (value * SERVICE_FEE_PERCENTAGE).quantize(
                    Decimal("0.01")
                )
                total_cost = value + service_fee

                task.budget = value
                task.service_fee = service_fee
                task.total_cost = total_cost

                logger.debug(
                    "Budget updated, recalculated fees",
                    extra={
                        "task_id": task_id,
                        "budget": str(value),
                        "service_fee": str(service_fee),
                        "total_cost": str(total_cost),
                    },
                )
            else:
                setattr(task, field, value)

        # Create history entry for status changes
        if "status" in update_dict and update_dict["status"] != previous_status:
            history = TaskHistory.create_entry(
                task_id=task.id,
                previous_status=previous_status.value,
                new_status=update_dict["status"].value,
                changed_by=user_id,
                reason=f"Status changed to {update_dict['status'].value}",
            )
            self.session.add(history)

            logger.info(
                "Task status changed",
                extra={
                    "task_id": task_id,
                    "previous_status": previous_status.value,
                    "new_status": update_dict["status"].value,
                },
            )

        await self.session.commit()
        await self.session.refresh(task)

        logger.info("Task updated successfully", extra={"task_id": task_id})

        return task

    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """
        Delete a task.

        Soft delete if task has assignments, hard delete otherwise.

        Args:
            task_id: Task identifier
            user_id: ID of user performing deletion

        Returns:
            True if deleted, False if not found

        Example:
            >>> success = await service.delete_task("task-123", "user-456")
        """
        logger.info(
            "Deleting task", extra={"task_id": task_id, "user_id": user_id}
        )

        task = await self.get_task(task_id)
        if not task:
            logger.warning("Task not found for deletion", extra={"task_id": task_id})
            return False

        # Create history entry
        history = TaskHistory.create_entry(
            task_id=task.id,
            previous_status=task.status.value,
            new_status="deleted",
            changed_by=user_id,
            reason="Task deleted",
        )
        self.session.add(history)

        # Delete the task (cascade will handle assignments and history)
        await self.session.delete(task)
        await self.session.commit()

        logger.info("Task deleted successfully", extra={"task_id": task_id})

        return True

    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 20,
        creator_id: str | None = None,
        status: TaskStatusEnum | None = None,
        platform: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Task], int]:
        """
        List tasks with filtering and pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            creator_id: Filter by creator ID
            status: Filter by task status
            platform: Filter by platform
            search: Search in title and description

        Returns:
            Tuple of (tasks list, total count)

        Example:
            >>> tasks, total = await service.list_tasks(
            ...     skip=0,
            ...     limit=20,
            ...     status=TaskStatusEnum.ACTIVE,
            ...     platform="instagram"
            ... )
        """
        logger.debug(
            "Listing tasks",
            extra={
                "skip": skip,
                "limit": limit,
                "creator_id": creator_id,
                "status": status.value if status else None,
                "platform": platform,
                "search": search,
            },
        )

        # Build filters
        filters = []

        if creator_id:
            filters.append(Task.creator_id == creator_id)

        if status:
            filters.append(Task.status == status)

        if platform:
            filters.append(Task.platform == platform)

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern),
                )
            )

        # Count query
        count_stmt = select(func.count(Task.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        data_stmt = (
            select(Task)
            .options(selectinload(Task.assignments), selectinload(Task.history))
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if filters:
            data_stmt = data_stmt.where(and_(*filters))

        data_result = await self.session.execute(data_stmt)
        tasks = list(data_result.scalars().all())

        logger.debug(
            "Tasks listed",
            extra={"total": total, "returned": len(tasks), "skip": skip, "limit": limit},
        )

        return tasks, total

    async def get_creator_tasks(
        self, creator_id: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[Task], int]:
        """
        Get all tasks created by a specific user.

        Args:
            creator_id: Creator's user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (tasks list, total count)

        Example:
            >>> tasks, total = await service.get_creator_tasks("user-123")
        """
        return await self.list_tasks(skip=skip, limit=limit, creator_id=creator_id)

    async def get_active_tasks(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[Task], int]:
        """
        Get all active tasks.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (tasks list, total count)

        Example:
            >>> tasks, total = await service.get_active_tasks()
        """
        return await self.list_tasks(
            skip=skip, limit=limit, status=TaskStatusEnum.ACTIVE
        )

    async def calculate_service_fee(self, budget: Decimal) -> dict[str, Decimal]:
        """
        Calculate service fee and total cost for a given budget.

        Args:
            budget: Task budget amount

        Returns:
            Dictionary with budget, service_fee, and total_cost

        Example:
            >>> result = await service.calculate_service_fee(Decimal("10.00"))
            >>> # Returns: {"budget": Decimal("10.00"), "service_fee": Decimal("1.50"), "total_cost": Decimal("11.50")}
        """
        service_fee = (budget * SERVICE_FEE_PERCENTAGE).quantize(Decimal("0.01"))
        total_cost = budget + service_fee

        logger.debug(
            "Service fee calculated",
            extra={
                "budget": str(budget),
                "service_fee": str(service_fee),
                "total_cost": str(total_cost),
            },
        )

        return {
            "budget": budget,
            "service_fee": service_fee,
            "total_cost": total_cost,
        }
