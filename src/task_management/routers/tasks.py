"""
Task Management API Endpoints.

Provides comprehensive REST API for task CRUD operations with proper
authentication, validation, pagination, and error handling.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user_id, get_database_session
from src.task_management.models.task import PlatformEnum, TaskStatusEnum
from src.task_management.schemas.task import (
    TaskCreate,
    TaskList,
    TaskResponse,
    TaskUpdate,
)
from src.task_management.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_task_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TaskService:
    """
    Dependency to get TaskService instance.

    Args:
        session: Database session from dependency

    Returns:
        TaskService instance
    """
    return TaskService(session)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task with automatic service fee calculation (15% of budget)",
)
async def create_task(
    task_data: TaskCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Create a new task.

    - **title**: Task title (3-255 characters)
    - **description**: Detailed description (10-5000 characters)
    - **instructions**: Step-by-step instructions (10-5000 characters)
    - **platform**: Social media platform
    - **task_type**: Type of task (like, comment, share, etc.)
    - **budget**: Payment per completion (must be positive, max 2 decimals)
    - **max_performers**: Maximum number of performers (1-10000)
    - **target_criteria**: Optional targeting rules (JSON)
    - **expires_at**: Optional expiration timestamp (must be future)

    Service fee (15%) and total cost are calculated automatically.
    Task is created in DRAFT status.

    Returns:
        Created task with all calculated fields
    """
    logger.info(
        "Creating task",
        extra={
            "user_id": user_id,
            "platform": task_data.platform.value,
            "task_type": task_data.task_type.value,
        },
    )

    try:
        task = await service.create_task(creator_id=user_id, task_data=task_data)

        logger.info(
            "Task created successfully",
            extra={"task_id": task.id, "user_id": user_id},
        )

        return TaskResponse.model_validate(task)

    except ValueError as e:
        logger.warning(
            "Task creation validation failed",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Task creation failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        )


@router.get(
    "",
    response_model=TaskList,
    summary="List tasks with filtering and pagination",
    description="Get a paginated list of tasks with optional filtering by status, platform, creator, and search",
)
async def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page (max 100)")
    ] = 20,
    status: Annotated[
        TaskStatusEnum | None, Query(description="Filter by task status")
    ] = None,
    platform: Annotated[
        PlatformEnum | None, Query(description="Filter by platform")
    ] = None,
    creator_id: Annotated[
        str | None, Query(description="Filter by creator user ID")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search in title and description")
    ] = None,
) -> TaskList:
    """
    List tasks with pagination and filtering.

    Query parameters:
    - **page**: Page number (1-indexed, default: 1)
    - **page_size**: Items per page (1-100, default: 20)
    - **status**: Filter by status (draft, active, completed, etc.)
    - **platform**: Filter by platform (facebook, instagram, twitter, etc.)
    - **creator_id**: Filter by creator's user ID
    - **search**: Search text in title and description

    Returns:
        Paginated list with tasks and metadata
    """
    logger.info(
        "Listing tasks",
        extra={
            "page": page,
            "page_size": page_size,
            "status": status.value if status else None,
            "platform": platform.value if platform else None,
            "creator_id": creator_id,
            "search": search,
        },
    )

    try:
        skip = (page - 1) * page_size

        tasks, total = await service.list_tasks(
            skip=skip,
            limit=page_size,
            creator_id=creator_id,
            status=status,
            platform=platform.value if platform else None,
            search=search,
        )

        total_pages = (total + page_size - 1) // page_size

        logger.info(
            "Tasks listed",
            extra={
                "total": total,
                "returned": len(tasks),
                "page": page,
                "total_pages": total_pages,
            },
        )

        return TaskList(
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(
            "Failed to list tasks",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks",
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
    description="Retrieve a single task by its unique identifier",
)
async def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Get a specific task by ID.

    Args:
        task_id: Unique task identifier

    Returns:
        Task details

    Raises:
        404: If task not found
    """
    logger.info("Fetching task", extra={"task_id": task_id})

    try:
        task = await service.get_task(task_id)

        if not task:
            logger.warning("Task not found", extra={"task_id": task_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        logger.info("Task retrieved", extra={"task_id": task_id})

        return TaskResponse.model_validate(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve task",
            extra={"task_id": task_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task",
        )


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update an existing task (partial updates supported)",
)
async def update_task(
    task_id: str,
    update_data: TaskUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """
    Update a task.

    All fields are optional for partial updates.
    If budget is updated, service fee and total cost are recalculated.
    Status changes create history entries.

    Args:
        task_id: Task identifier
        update_data: Fields to update (partial)
        user_id: Current user ID (from auth)
        service: Task service instance

    Returns:
        Updated task

    Raises:
        404: If task not found
        400: If validation fails
        403: If user is not the creator
    """
    logger.info(
        "Updating task",
        extra={"task_id": task_id, "user_id": user_id},
    )

    try:
        # Get existing task to check ownership
        existing_task = await service.get_task(task_id)

        if not existing_task:
            logger.warning(
                "Task not found for update",
                extra={"task_id": task_id, "user_id": user_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Check ownership
        if existing_task.creator_id != user_id:
            logger.warning(
                "Unauthorized task update attempt",
                extra={
                    "task_id": task_id,
                    "user_id": user_id,
                    "creator_id": existing_task.creator_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own tasks",
            )

        # Perform update
        task = await service.update_task(
            task_id=task_id, user_id=user_id, update_data=update_data
        )

        if not task:
            # Shouldn't happen as we already checked, but safety check
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        logger.info(
            "Task updated successfully",
            extra={"task_id": task_id, "user_id": user_id},
        )

        return TaskResponse.model_validate(task)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Task update validation failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Task update failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task",
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task (only task creator can delete)",
)
async def delete_task(
    task_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """
    Delete a task.

    Only the task creator can delete their own tasks.
    Deletion cascades to assignments and history.

    Args:
        task_id: Task identifier
        user_id: Current user ID (from auth)
        service: Task service instance

    Raises:
        404: If task not found
        403: If user is not the creator
    """
    logger.info(
        "Deleting task",
        extra={"task_id": task_id, "user_id": user_id},
    )

    try:
        # Get existing task to check ownership
        existing_task = await service.get_task(task_id)

        if not existing_task:
            logger.warning(
                "Task not found for deletion",
                extra={"task_id": task_id, "user_id": user_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Check ownership
        if existing_task.creator_id != user_id:
            logger.warning(
                "Unauthorized task deletion attempt",
                extra={
                    "task_id": task_id,
                    "user_id": user_id,
                    "creator_id": existing_task.creator_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own tasks",
            )

        # Perform deletion
        success = await service.delete_task(task_id=task_id, user_id=user_id)

        if not success:
            # Shouldn't happen as we already checked, but safety check
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        logger.info(
            "Task deleted successfully",
            extra={"task_id": task_id, "user_id": user_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Task deletion failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task",
        )
