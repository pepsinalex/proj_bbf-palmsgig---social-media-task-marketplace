"""
Task Creation and Draft Management API Endpoints.

Provides REST API for creating task drafts, publishing tasks,
and managing drafts with proper validation and error handling.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user_id, get_database_session
from src.task_management.schemas.task_creation import (
    TaskCreationResponse,
    TaskDraftCreate,
    TaskPublishRequest,
)
from src.task_management.services.fee_service import FeeService
from src.task_management.services.task_service import TaskService
from src.task_management.services.validation_service import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["task-creation"])


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
    "/draft",
    response_model=TaskCreationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task draft",
    description="Create a task draft that can be completed and published later",
)
async def create_draft(
    draft_data: TaskDraftCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskCreationResponse:
    """
    Create a task draft.

    Drafts allow users to save incomplete tasks and complete them later.
    Only title is required for drafts - all other fields are optional.

    - **title**: Task title (required, 3-255 characters)
    - **description**: Detailed description (optional, 10-5000 characters)
    - **instructions**: Step-by-step instructions (optional, 10-5000 characters)
    - **platform**: Social media platform (optional)
    - **task_type**: Type of task (optional)
    - **budget**: Payment per completion (optional, must be positive)
    - **max_performers**: Maximum performers (optional, 1-10000)
    - **target_criteria**: Optional targeting rules (optional, JSON)
    - **expires_at**: Optional expiration timestamp (optional)

    Returns:
        Created draft with status DRAFT
    """
    logger.info(
        "Creating task draft",
        extra={"user_id": user_id, "title": draft_data.title},
    )

    try:
        draft = await service.create_draft(
            creator_id=user_id, draft_data=draft_data
        )

        # Build response with fee breakdown if budget is provided
        fee_breakdown = None
        if draft_data.budget and draft_data.max_performers:
            fee_breakdown = FeeService.calculate_fee_breakdown(
                draft_data.budget, draft_data.max_performers
            )

        response = TaskCreationResponse(
            id=draft.id,
            creator_id=draft.creator_id,
            title=draft.title,
            description=draft.description if draft.description else None,
            instructions=draft.instructions if draft.instructions else None,
            platform=draft.platform,
            task_type=draft.task_type,
            budget=draft.budget if draft.budget > 0 else None,
            service_fee=draft.service_fee,
            total_cost=draft.total_cost,
            max_performers=(
                draft.max_performers if draft.max_performers > 0 else None
            ),
            current_performers=draft.current_performers,
            status=draft.status,
            target_criteria=draft.target_criteria,
            expires_at=draft.expires_at,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            fee_breakdown=fee_breakdown,
        )

        logger.info(
            "Draft created successfully",
            extra={"task_id": draft.id, "user_id": user_id},
        )

        return response

    except ValidationError as e:
        logger.warning(
            "Draft creation validation failed",
            extra={"user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Draft creation failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create draft",
        )


@router.post(
    "/{task_id}/publish",
    response_model=TaskCreationResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish a task draft",
    description="Publish a draft task after completing all required fields",
)
async def publish_task(
    task_id: str,
    publish_data: TaskPublishRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskCreationResponse:
    """
    Publish a task draft.

    All required fields must be provided to publish a draft.
    Task status will transition from DRAFT to PENDING_PAYMENT.

    Required fields:
    - **title**: Task title (3-255 characters)
    - **description**: Detailed description (10-5000 characters)
    - **instructions**: Step-by-step instructions (10-5000 characters)
    - **platform**: Social media platform
    - **task_type**: Type of task (must be compatible with platform)
    - **budget**: Payment per completion (must be positive)
    - **max_performers**: Maximum performers (1-10000)

    Optional fields:
    - **target_criteria**: Targeting rules (JSON)
    - **expires_at**: Expiration timestamp

    Returns:
        Published task with status PENDING_PAYMENT

    Raises:
        404: If task not found
        400: If validation fails or task is not a draft
        403: If user is not the creator
    """
    logger.info(
        "Publishing task",
        extra={"task_id": task_id, "user_id": user_id},
    )

    try:
        # Check task exists and user is creator
        existing_task = await service.get_draft(task_id, user_id)

        if not existing_task:
            # Check if task exists at all
            task = await service.get_task(task_id)
            if not task:
                logger.warning(
                    "Task not found for publishing",
                    extra={"task_id": task_id, "user_id": user_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found",
                )
            elif task.creator_id != user_id:
                logger.warning(
                    "Unauthorized task publish attempt",
                    extra={
                        "task_id": task_id,
                        "user_id": user_id,
                        "creator_id": task.creator_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only publish your own tasks",
                )
            else:
                logger.warning(
                    "Task is not a draft",
                    extra={
                        "task_id": task_id,
                        "status": task.status.value,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task is not a draft (status: {task.status.value})",
                )

        # Publish the task
        task = await service.publish_task(
            task_id=task_id, user_id=user_id, publish_data=publish_data
        )

        # Build response with fee breakdown
        fee_breakdown = FeeService.calculate_fee_breakdown(
            task.budget, task.max_performers
        )

        response = TaskCreationResponse(
            id=task.id,
            creator_id=task.creator_id,
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
            target_criteria=task.target_criteria,
            expires_at=task.expires_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            fee_breakdown=fee_breakdown,
        )

        logger.info(
            "Task published successfully",
            extra={
                "task_id": task_id,
                "user_id": user_id,
                "status": task.status.value,
            },
        )

        return response

    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(
            "Task publish validation failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(
            "Task publish failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Task publish failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish task",
        )


@router.get(
    "/drafts",
    response_model=list[TaskCreationResponse],
    summary="List user's task drafts",
    description="Get a list of all draft tasks created by the current user",
)
async def list_drafts(
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
    skip: Annotated[
        int, Query(ge=0, description="Number of records to skip")
    ] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum records to return")
    ] = 20,
) -> list[TaskCreationResponse]:
    """
    List all draft tasks for the current user.

    Query parameters:
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (1-100, default: 20)

    Returns:
        List of draft tasks
    """
    logger.info(
        "Listing drafts",
        extra={"user_id": user_id, "skip": skip, "limit": limit},
    )

    try:
        drafts, total = await service.list_drafts(
            creator_id=user_id, skip=skip, limit=limit
        )

        responses = []
        for draft in drafts:
            # Build fee breakdown if budget and max_performers are set
            fee_breakdown = None
            if draft.budget and draft.budget > 0 and draft.max_performers > 0:
                fee_breakdown = FeeService.calculate_fee_breakdown(
                    draft.budget, draft.max_performers
                )

            response = TaskCreationResponse(
                id=draft.id,
                creator_id=draft.creator_id,
                title=draft.title,
                description=draft.description if draft.description else None,
                instructions=(
                    draft.instructions if draft.instructions else None
                ),
                platform=draft.platform,
                task_type=draft.task_type,
                budget=draft.budget if draft.budget > 0 else None,
                service_fee=draft.service_fee,
                total_cost=draft.total_cost,
                max_performers=(
                    draft.max_performers if draft.max_performers > 0 else None
                ),
                current_performers=draft.current_performers,
                status=draft.status,
                target_criteria=draft.target_criteria,
                expires_at=draft.expires_at,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
                fee_breakdown=fee_breakdown,
            )
            responses.append(response)

        logger.info(
            "Drafts listed",
            extra={
                "user_id": user_id,
                "total": total,
                "returned": len(responses),
            },
        )

        return responses

    except Exception as e:
        logger.error(
            "Failed to list drafts",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve drafts",
        )


@router.put(
    "/drafts/{draft_id}",
    response_model=TaskCreationResponse,
    summary="Update a task draft",
    description="Update an existing task draft",
)
async def update_draft(
    draft_id: str,
    draft_data: TaskDraftCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskCreationResponse:
    """
    Update a task draft.

    Only drafts (tasks with DRAFT status) can be updated with this endpoint.
    All fields are optional for partial updates.

    Args:
        draft_id: Draft task identifier
        draft_data: Draft update data
        user_id: Current user ID (from auth)
        service: Task service instance

    Returns:
        Updated draft

    Raises:
        404: If draft not found
        400: If validation fails or task is not a draft
        403: If user is not the creator
    """
    logger.info(
        "Updating draft",
        extra={"draft_id": draft_id, "user_id": user_id},
    )

    try:
        # Verify draft exists and user is creator
        existing_draft = await service.get_draft(draft_id, user_id)

        if not existing_draft:
            # Check if task exists at all
            task = await service.get_task(draft_id)
            if not task:
                logger.warning(
                    "Draft not found",
                    extra={"draft_id": draft_id, "user_id": user_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Draft {draft_id} not found",
                )
            elif task.creator_id != user_id:
                logger.warning(
                    "Unauthorized draft update attempt",
                    extra={
                        "draft_id": draft_id,
                        "user_id": user_id,
                        "creator_id": task.creator_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own drafts",
                )
            else:
                logger.warning(
                    "Task is not a draft",
                    extra={
                        "draft_id": draft_id,
                        "status": task.status.value,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task is not a draft (status: {task.status.value})",
                )

        # Update the draft
        draft = await service.update_draft(
            task_id=draft_id, user_id=user_id, draft_data=draft_data
        )

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found",
            )

        # Build response with fee breakdown if budget is provided
        fee_breakdown = None
        if draft.budget and draft.budget > 0 and draft.max_performers > 0:
            fee_breakdown = FeeService.calculate_fee_breakdown(
                draft.budget, draft.max_performers
            )

        response = TaskCreationResponse(
            id=draft.id,
            creator_id=draft.creator_id,
            title=draft.title,
            description=draft.description if draft.description else None,
            instructions=draft.instructions if draft.instructions else None,
            platform=draft.platform,
            task_type=draft.task_type,
            budget=draft.budget if draft.budget > 0 else None,
            service_fee=draft.service_fee,
            total_cost=draft.total_cost,
            max_performers=(
                draft.max_performers if draft.max_performers > 0 else None
            ),
            current_performers=draft.current_performers,
            status=draft.status,
            target_criteria=draft.target_criteria,
            expires_at=draft.expires_at,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            fee_breakdown=fee_breakdown,
        )

        logger.info(
            "Draft updated successfully",
            extra={"draft_id": draft_id, "user_id": user_id},
        )

        return response

    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(
            "Draft update validation failed",
            extra={"draft_id": draft_id, "user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(
            "Draft update failed",
            extra={"draft_id": draft_id, "user_id": user_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Draft update failed",
            extra={"draft_id": draft_id, "user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update draft",
        )


@router.delete(
    "/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task draft",
    description="Delete a draft task (only creator can delete)",
)
async def delete_draft(
    draft_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> None:
    """
    Delete a task draft.

    Only the draft creator can delete their own drafts.
    Only tasks in DRAFT status can be deleted with this endpoint.

    Args:
        draft_id: Draft task identifier
        user_id: Current user ID (from auth)
        service: Task service instance

    Raises:
        404: If draft not found
        400: If task is not a draft
        403: If user is not the creator
    """
    logger.info(
        "Deleting draft",
        extra={"draft_id": draft_id, "user_id": user_id},
    )

    try:
        # Verify draft exists and user is creator
        existing_draft = await service.get_draft(draft_id, user_id)

        if not existing_draft:
            # Check if task exists at all
            task = await service.get_task(draft_id)
            if not task:
                logger.warning(
                    "Draft not found for deletion",
                    extra={"draft_id": draft_id, "user_id": user_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Draft {draft_id} not found",
                )
            elif task.creator_id != user_id:
                logger.warning(
                    "Unauthorized draft deletion attempt",
                    extra={
                        "draft_id": draft_id,
                        "user_id": user_id,
                        "creator_id": task.creator_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own drafts",
                )
            else:
                logger.warning(
                    "Task is not a draft",
                    extra={
                        "draft_id": draft_id,
                        "status": task.status.value,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task is not a draft (status: {task.status.value})",
                )

        # Delete the draft
        success = await service.delete_task(task_id=draft_id, user_id=user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found",
            )

        logger.info(
            "Draft deleted successfully",
            extra={"draft_id": draft_id, "user_id": user_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Draft deletion failed",
            extra={"draft_id": draft_id, "user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete draft",
        )
