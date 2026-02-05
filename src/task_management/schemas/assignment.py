"""
Task Assignment Schemas.

Provides request/response schemas for task assignment operations
with validation and proper error handling.
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.task_management.models.task_assignment import AssignmentStatusEnum

logger = logging.getLogger(__name__)


class TaskAssignmentRequest(BaseModel):
    """
    Request schema for assigning a task to a performer.
    """

    task_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="ID of the task to assign",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )

    model_config = {"from_attributes": True}


class AssignmentMetadata(BaseModel):
    """
    Additional metadata about an assignment.
    """

    task_title: Optional[str] = Field(
        default=None, description="Title of the assigned task"
    )
    task_platform: Optional[str] = Field(
        default=None, description="Platform of the task"
    )
    task_type: Optional[str] = Field(default=None, description="Type of the task")
    task_budget: Optional[float] = Field(
        default=None, description="Budget for the task"
    )

    model_config = {"from_attributes": True}


class AssignmentStatus(BaseModel):
    """
    Status information for an assignment.
    """

    status: AssignmentStatusEnum = Field(..., description="Current assignment status")
    assigned_at: datetime = Field(..., description="Assignment timestamp")
    started_at: Optional[datetime] = Field(
        default=None, description="Start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    proof_submitted_at: Optional[datetime] = Field(
        default=None, description="Proof submission timestamp"
    )
    verified_at: Optional[datetime] = Field(
        default=None, description="Verification timestamp"
    )

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    """
    Response schema for assignment operations.
    """

    id: str = Field(..., description="Assignment ID")
    task_id: str = Field(..., description="Task ID")
    performer_id: str = Field(..., description="Performer ID")
    status: AssignmentStatusEnum = Field(..., description="Assignment status")
    assigned_at: datetime = Field(..., description="Assignment timestamp")
    started_at: Optional[datetime] = Field(
        default=None, description="Start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    proof_submitted_at: Optional[datetime] = Field(
        default=None, description="Proof submission timestamp"
    )
    verified_at: Optional[datetime] = Field(
        default=None, description="Verification timestamp"
    )
    rating: Optional[int] = Field(
        default=None, ge=1, le=5, description="Rating (1-5)"
    )
    review: Optional[str] = Field(default=None, description="Review text")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    model_config = {"from_attributes": True}


class UserAssignments(BaseModel):
    """
    Response schema for user's assignments list.
    """

    assignments: list[AssignmentResponse] = Field(
        ..., description="List of assignments"
    )
    total: int = Field(..., description="Total number of assignments")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")

    model_config = {"from_attributes": True}


class AssignmentActionRequest(BaseModel):
    """
    Request schema for assignment actions (start, submit proof, etc.).
    """

    action: str = Field(
        ...,
        description="Action to perform",
        examples=["start", "submit_proof", "cancel"],
    )
    proof_url: Optional[str] = Field(
        default=None,
        description="URL to proof (for submit_proof action)",
        examples=["https://example.com/proof.png"],
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional notes about the action",
    )

    model_config = {"from_attributes": True}


class AssignmentEligibilityCheck(BaseModel):
    """
    Response schema for checking assignment eligibility.
    """

    eligible: bool = Field(..., description="Whether user is eligible")
    reason: Optional[str] = Field(
        default=None, description="Reason if not eligible"
    )
    concurrent_tasks: Optional[int] = Field(
        default=None, description="Current concurrent task count"
    )
    max_concurrent: Optional[int] = Field(
        default=None, description="Maximum concurrent tasks allowed"
    )

    model_config = {"from_attributes": True}
