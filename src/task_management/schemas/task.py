"""
Task Pydantic Schemas.

Provides request/response schemas for task management API endpoints
with comprehensive validation and serialization.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.task_management.models.task import PlatformEnum, TaskStatusEnum, TaskTypeEnum

logger = logging.getLogger(__name__)


class TaskBase(BaseModel):
    """
    Base schema for task with common fields.

    Used as a foundation for create/update schemas.
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Task title/summary",
        examples=["Like my Instagram post"],
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed task description",
        examples=["Need 100 likes on my latest Instagram post about travel"],
    )

    instructions: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Step-by-step instructions for performers",
        examples=[
            "1. Visit the Instagram post URL\n2. Click the like button\n3. Take a screenshot as proof"
        ],
    )

    platform: PlatformEnum = Field(
        ..., description="Social media platform", examples=["instagram"]
    )

    task_type: TaskTypeEnum = Field(
        ..., description="Type of task", examples=["like"]
    )

    budget: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Budget per task completion (performer payment in USD)",
        examples=[0.50],
    )

    max_performers: int = Field(
        ...,
        gt=0,
        le=10000,
        description="Maximum number of performers allowed",
        examples=[100],
    )

    target_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON targeting criteria (location, demographics, etc.)",
        examples=[
            {
                "countries": ["US", "CA", "UK"],
                "min_age": 18,
                "max_age": 45,
                "languages": ["en"],
            }
        ],
    )

    expires_at: datetime | None = Field(
        default=None,
        description="Optional task expiration timestamp",
        examples=["2026-03-01T00:00:00Z"],
    )

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Decimal) -> Decimal:
        """Validate budget is positive and has max 2 decimal places."""
        if v <= 0:
            raise ValueError("Budget must be positive")
        if v.as_tuple().exponent < -2:
            raise ValueError("Budget must have at most 2 decimal places")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """Validate expiration date is in the future."""
        if v is not None and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v

    model_config = {"from_attributes": True, "use_enum_values": False}


class TaskCreate(TaskBase):
    """
    Schema for creating a new task.

    Inherits all fields from TaskBase. Creator ID will be set from authentication.
    Service fee and total cost will be calculated automatically.
    """

    pass


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.

    All fields are optional for partial updates.
    """

    title: str | None = Field(
        default=None, min_length=3, max_length=255, description="Task title/summary"
    )

    description: str | None = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Detailed task description",
    )

    instructions: str | None = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Step-by-step instructions",
    )

    budget: Decimal | None = Field(
        default=None, gt=0, decimal_places=2, description="Budget per completion"
    )

    max_performers: int | None = Field(
        default=None, gt=0, le=10000, description="Maximum performers"
    )

    target_criteria: dict[str, Any] | None = Field(
        default=None, description="Targeting criteria"
    )

    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")

    status: TaskStatusEnum | None = Field(default=None, description="Task status")

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Decimal | None) -> Decimal | None:
        """Validate budget if provided."""
        if v is not None:
            if v <= 0:
                raise ValueError("Budget must be positive")
            if v.as_tuple().exponent < -2:
                raise ValueError("Budget must have at most 2 decimal places")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """Validate expiration date if provided."""
        if v is not None and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v

    model_config = {"from_attributes": True, "use_enum_values": False}


class TaskResponse(TaskBase):
    """
    Schema for task response.

    Includes all task fields plus computed/system fields.
    """

    id: str = Field(..., description="Unique task identifier")

    creator_id: str = Field(..., description="User ID of task creator")

    service_fee: Decimal = Field(
        ..., description="Platform service fee (15% of budget)"
    )

    total_cost: Decimal = Field(..., description="Total cost (budget + service_fee)")

    status: TaskStatusEnum = Field(..., description="Current task status")

    current_performers: int = Field(
        ..., description="Current number of assigned performers"
    )

    created_at: datetime = Field(..., description="Task creation timestamp")

    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True, "use_enum_values": False}


class TaskList(BaseModel):
    """
    Schema for paginated task list response.

    Provides structured pagination metadata along with task data.
    """

    tasks: list[TaskResponse] = Field(..., description="List of tasks")

    total: int = Field(..., description="Total number of tasks matching query")

    page: int = Field(..., description="Current page number (1-indexed)")

    page_size: int = Field(..., description="Number of tasks per page")

    total_pages: int = Field(..., description="Total number of pages")

    model_config = {"from_attributes": True}
