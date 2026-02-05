"""
Task Assignment Router.

Provides API endpoints for task assignment operations including
assignment, unassignment, and status tracking.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database import get_db_session
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)
from src.task_management.schemas.assignment import (
    AssignmentEligibilityCheck,
    AssignmentResponse,
    TaskAssignmentRequest,
    UserAssignments,
)
from src.task_management.services.assignment_service import AssignmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assignments", tags=["Task Assignments"])


def get_assignment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AssignmentService:
    """
    Dependency to get assignment service instance.

    Args:
        session: Database session

    Returns:
        AssignmentService instance
    """
    return AssignmentService(session)


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign task to performer",
)
async def assign_task(
    request: TaskAssignmentRequest,
    performer_id: Annotated[str, Query(description="ID of the performer")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assignment_service: Annotated[
        AssignmentService, Depends(get_assignment_service)
    ],
) -> AssignmentResponse:
    """
    Assign a task to a performer.

    Validates performer eligibility, concurrent task limits, and creates assignment.
    """
    # Get task
    task = await session.get(Task, request.task_id)
    if not task:
        logger.warning(
            "Task not found for assignment",
            extra={"task_id": request.task_id, "performer_id": performer_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Assign task
    assignment, error_msg = await assignment_service.assign_task(
        task=task, performer_id=performer_id
    )

    if not assignment:
        logger.warning(
            "Task assignment failed",
            extra={
                "task_id": request.task_id,
                "performer_id": performer_id,
                "error": error_msg,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg or "Assignment failed"
        )

    # Commit transaction
    await session.commit()
    await session.refresh(assignment)

    logger.info(
        "Task assigned successfully",
        extra={
            "task_id": task.id,
            "performer_id": performer_id,
            "assignment_id": assignment.id,
        },
    )

    return AssignmentResponse.model_validate(assignment)


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_200_OK,
    summary="Unassign task from performer",
)
async def unassign_task(
    assignment_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assignment_service: Annotated[
        AssignmentService, Depends(get_assignment_service)
    ],
) -> dict:
    """
    Unassign a task from a performer (cancel assignment).

    Cancels the assignment and decrements task performer count.
    """
    # Get assignment
    assignment = await session.get(TaskAssignment, assignment_id)
    if not assignment:
        logger.warning(
            "Assignment not found for unassignment",
            extra={"assignment_id": assignment_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    # Unassign task
    success, error_msg = await assignment_service.unassign_task(assignment)

    if not success:
        logger.error(
            "Failed to unassign task",
            extra={"assignment_id": assignment_id, "error": error_msg},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "Unassignment failed",
        )

    # Commit transaction
    await session.commit()

    logger.info(
        "Task unassigned successfully",
        extra={"assignment_id": assignment_id},
    )

    return {"success": True, "message": "Task unassigned successfully"}


@router.get(
    "/user/{user_id}",
    response_model=UserAssignments,
    summary="Get user's assignments",
)
async def get_user_assignments(
    user_id: str,
    status_filter: Annotated[Optional[AssignmentStatusEnum], Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assignment_service: Annotated[
        AssignmentService, Depends(get_assignment_service)
    ],
) -> UserAssignments:
    """
    Get assignments for a user with optional status filter.

    Returns paginated list of assignments with metadata.
    """
    assignments = await assignment_service.get_user_assignments(
        performer_id=user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    logger.info(
        "Retrieved user assignments",
        extra={
            "user_id": user_id,
            "count": len(assignments),
            "status": status_filter.value if status_filter else None,
        },
    )

    assignment_responses = [
        AssignmentResponse.model_validate(a) for a in assignments
    ]

    return UserAssignments(
        assignments=assignment_responses,
        total=len(assignments),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Get assignment details",
)
async def get_assignment(
    assignment_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AssignmentResponse:
    """
    Get details of a specific assignment.
    """
    assignment = await session.get(TaskAssignment, assignment_id)
    if not assignment:
        logger.warning(
            "Assignment not found",
            extra={"assignment_id": assignment_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    logger.info(
        "Retrieved assignment details",
        extra={"assignment_id": assignment_id},
    )

    return AssignmentResponse.model_validate(assignment)


@router.get(
    "/eligibility/check",
    response_model=AssignmentEligibilityCheck,
    summary="Check assignment eligibility",
)
async def check_eligibility(
    performer_id: Annotated[str, Query(description="ID of the performer")],
    task_id: Annotated[str, Query(description="ID of the task")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assignment_service: Annotated[
        AssignmentService, Depends(get_assignment_service)
    ],
) -> AssignmentEligibilityCheck:
    """
    Check if a performer is eligible to accept a task.

    Validates eligibility without creating an assignment.
    """
    # Get task
    task = await session.get(Task, task_id)
    if not task:
        logger.warning(
            "Task not found for eligibility check",
            extra={"task_id": task_id, "performer_id": performer_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Check eligibility
    is_eligible, reason = await assignment_service.validate_performer_eligibility(
        performer_id=performer_id, task=task
    )

    # Get concurrent task info
    current_count, max_allowed = await assignment_service.check_concurrent_limits(
        performer_id=performer_id
    )

    logger.info(
        "Checked assignment eligibility",
        extra={
            "performer_id": performer_id,
            "task_id": task_id,
            "eligible": is_eligible,
        },
    )

    return AssignmentEligibilityCheck(
        eligible=is_eligible,
        reason=reason,
        concurrent_tasks=current_count,
        max_concurrent=max_allowed,
    )
