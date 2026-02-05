"""
Task Creation Schemas.

Provides request/response schemas for task creation and draft management
with comprehensive validation and fee breakdown calculations.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.task_management.enums.task_enums import (
    PlatformEnum,
    TaskStatusEnum,
    TaskTypeEnum,
)

logger = logging.getLogger(__name__)


class FeeBreakdown(BaseModel):
    """
    Fee breakdown for task cost calculation.

    Provides detailed breakdown of budget, service fee, and total cost.
    """

    budget: Decimal = Field(
        ...,
        description="Budget per task completion (performer payment)",
        examples=[Decimal("10.00")],
    )

    service_fee: Decimal = Field(
        ...,
        description="Platform service fee (15% of budget)",
        examples=[Decimal("1.50")],
    )

    service_fee_percentage: Decimal = Field(
        default=Decimal("0.15"),
        description="Service fee percentage",
        examples=[Decimal("0.15")],
    )

    total_cost: Decimal = Field(
        ...,
        description="Total cost per task (budget + service_fee)",
        examples=[Decimal("11.50")],
    )

    total_cost_all_performers: Decimal = Field(
        ...,
        description="Total cost for all performers (total_cost * max_performers)",
        examples=[Decimal("1150.00")],
    )

    model_config = {"from_attributes": True}


class TaskDraftCreate(BaseModel):
    """
    Schema for creating a task draft.

    Task drafts allow users to save incomplete tasks and complete them later.
    All fields are optional except the basic required fields.
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Task title/summary",
        examples=["Like my Instagram post"],
    )

    description: str | None = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Detailed task description",
        examples=["Need 100 likes on my latest Instagram post about travel"],
    )

    instructions: str | None = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Step-by-step instructions for performers",
        examples=[
            "1. Visit the Instagram post URL\n"
            "2. Click the like button\n"
            "3. Take a screenshot as proof"
        ],
    )

    platform: PlatformEnum | None = Field(
        default=None,
        description="Social media platform",
        examples=["instagram"],
    )

    task_type: TaskTypeEnum | None = Field(
        default=None, description="Type of task", examples=["like"]
    )

    budget: Decimal | None = Field(
        default=None,
        gt=0,
        decimal_places=2,
        description="Budget per task completion (performer payment in USD)",
        examples=[Decimal("0.50")],
    )

    max_performers: int | None = Field(
        default=None,
        gt=0,
        le=10000,
        description="Maximum number of performers allowed",
        examples=[100],
    )

    target_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON targeting criteria",
        examples=[
            {
                "countries": ["US", "CA", "UK"],
                "min_age": 18,
                "max_age": 45,
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
    def validate_budget(cls, v: Decimal | None) -> Decimal | None:
        """Validate budget is positive and has max 2 decimal places."""
        if v is not None:
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


class TaskPublishRequest(BaseModel):
    """
    Schema for publishing a draft task.

    Contains all required fields that must be present to publish a draft.
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Task title/summary",
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed task description",
    )

    instructions: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Step-by-step instructions for performers",
    )

    platform: PlatformEnum = Field(..., description="Social media platform")

    task_type: TaskTypeEnum = Field(..., description="Type of task")

    budget: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Budget per task completion (performer payment in USD)",
    )

    max_performers: int = Field(
        ...,
        gt=0,
        le=10000,
        description="Maximum number of performers allowed",
    )

    target_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON targeting criteria",
    )

    expires_at: datetime | None = Field(
        default=None,
        description="Optional task expiration timestamp",
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


class TaskCreationResponse(BaseModel):
    """
    Schema for task creation response.

    Includes all task fields plus computed/system fields and fee breakdown.
    """

    id: str = Field(..., description="Unique task identifier")

    creator_id: str = Field(..., description="User ID of task creator")

    title: str = Field(..., description="Task title/summary")

    description: str | None = Field(default=None, description="Task description")

    instructions: str | None = Field(
        default=None, description="Task instructions"
    )

    platform: PlatformEnum | None = Field(
        default=None, description="Social media platform"
    )

    task_type: TaskTypeEnum | None = Field(
        default=None, description="Type of task"
    )

    budget: Decimal | None = Field(
        default=None, description="Budget per task completion"
    )

    service_fee: Decimal = Field(..., description="Platform service fee")

    total_cost: Decimal = Field(..., description="Total cost per task")

    max_performers: int | None = Field(
        default=None, description="Maximum number of performers"
    )

    current_performers: int = Field(
        ..., description="Current number of assigned performers"
    )

    status: TaskStatusEnum = Field(..., description="Current task status")

    target_criteria: dict[str, Any] | None = Field(
        default=None, description="Targeting criteria"
    )

    expires_at: datetime | None = Field(
        default=None, description="Task expiration timestamp"
    )

    created_at: datetime = Field(..., description="Task creation timestamp")

    updated_at: datetime = Field(..., description="Last update timestamp")

    fee_breakdown: FeeBreakdown | None = Field(
        default=None, description="Detailed fee breakdown"
    )

    model_config = {"from_attributes": True, "use_enum_values": False}
