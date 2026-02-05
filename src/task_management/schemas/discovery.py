"""
Task Discovery and Search Schemas.

Provides comprehensive schemas for task discovery, filtering, search operations,
and recommendation responses with pagination support.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum

logger = logging.getLogger(__name__)


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.

    Provides standardized pagination controls with validation.
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
        examples=[1],
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
        examples=[20],
    )

    @property
    def offset(self) -> int:
        """Calculate database offset from page and page_size."""
        return (self.page - 1) * self.page_size

    model_config = {"from_attributes": True}


class TaskFilter(BaseModel):
    """
    Comprehensive filtering options for task discovery.

    Supports filtering by platform, type, status, budget range,
    creator, and expiration criteria.
    """

    platform: PlatformEnum | None = Field(
        default=None,
        description="Filter by social media platform",
        examples=["instagram"],
    )

    task_type: TaskTypeEnum | None = Field(
        default=None,
        description="Filter by task type",
        examples=["like"],
    )

    status: TaskStatusEnum | None = Field(
        default=None,
        description="Filter by task status",
        examples=["active"],
    )

    min_budget: Decimal | None = Field(
        default=None,
        ge=0,
        description="Minimum budget per task completion",
        examples=[0.50],
    )

    max_budget: Decimal | None = Field(
        default=None,
        ge=0,
        description="Maximum budget per task completion",
        examples=[5.00],
    )

    creator_id: str | None = Field(
        default=None,
        description="Filter by task creator user ID",
        examples=["user_123"],
    )

    exclude_expired: bool = Field(
        default=True,
        description="Exclude expired tasks from results",
        examples=[True],
    )

    exclude_full: bool = Field(
        default=True,
        description="Exclude tasks with max performers reached",
        examples=[True],
    )

    sort_by: str = Field(
        default="created_at",
        description="Sort field (created_at, budget, expires_at)",
        examples=["created_at"],
    )

    sort_order: str = Field(
        default="desc",
        description="Sort order (asc or desc)",
        examples=["desc"],
    )

    @field_validator("min_budget", "max_budget")
    @classmethod
    def validate_budget_values(cls, v: Decimal | None) -> Decimal | None:
        """Validate budget values if provided."""
        if v is not None and v < 0:
            raise ValueError("Budget values must be non-negative")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field."""
        valid_fields = {"created_at", "budget", "expires_at", "current_performers"}
        if v not in valid_fields:
            raise ValueError(
                f"Invalid sort_by field: {v}. "
                f"Valid fields: {', '.join(sorted(valid_fields))}"
            )
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort_order value."""
        v_lower = v.lower()
        if v_lower not in {"asc", "desc"}:
            raise ValueError(f"Invalid sort_order: {v}. Must be 'asc' or 'desc'")
        return v_lower

    model_config = {"from_attributes": True, "use_enum_values": False}


class TaskSearch(BaseModel):
    """
    Full-text search parameters for task discovery.

    Supports searching across task title, description, and instructions
    with Elasticsearch integration.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string",
        examples=["Instagram like post"],
    )

    search_fields: list[str] = Field(
        default=["title", "description", "instructions"],
        description="Fields to search in",
        examples=[["title", "description"]],
    )

    boost_title: float = Field(
        default=3.0,
        ge=0,
        description="Boost factor for title field",
        examples=[3.0],
    )

    boost_description: float = Field(
        default=1.5,
        ge=0,
        description="Boost factor for description field",
        examples=[1.5],
    )

    boost_instructions: float = Field(
        default=1.0,
        ge=0,
        description="Boost factor for instructions field",
        examples=[1.0],
    )

    fuzzy: bool = Field(
        default=True,
        description="Enable fuzzy matching for typo tolerance",
        examples=[True],
    )

    @field_validator("search_fields")
    @classmethod
    def validate_search_fields(cls, v: list[str]) -> list[str]:
        """Validate search fields."""
        if not v:
            raise ValueError("At least one search field must be specified")

        valid_fields = {"title", "description", "instructions"}
        invalid_fields = set(v) - valid_fields
        if invalid_fields:
            raise ValueError(
                f"Invalid search fields: {', '.join(invalid_fields)}. "
                f"Valid fields: {', '.join(sorted(valid_fields))}"
            )
        return v

    model_config = {"from_attributes": True}


class TaskDiscoveryResponse(BaseModel):
    """
    Response schema for task discovery endpoints.

    Includes task data along with pagination metadata and optional
    search relevance scores.
    """

    id: str = Field(..., description="Unique task identifier")

    title: str = Field(..., description="Task title/summary")

    description: str = Field(..., description="Detailed task description")

    instructions: str = Field(..., description="Task instructions")

    platform: PlatformEnum = Field(..., description="Social media platform")

    task_type: TaskTypeEnum = Field(..., description="Type of task")

    budget: Decimal = Field(..., description="Budget per task completion in USD")

    service_fee: Decimal = Field(..., description="Platform service fee")

    total_cost: Decimal = Field(..., description="Total cost (budget + service_fee)")

    max_performers: int = Field(..., description="Maximum number of performers")

    current_performers: int = Field(..., description="Current assigned performers")

    status: TaskStatusEnum = Field(..., description="Current task status")

    creator_id: str = Field(..., description="Task creator user ID")

    target_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Optional targeting criteria",
    )

    expires_at: datetime | None = Field(
        default=None,
        description="Task expiration timestamp",
    )

    created_at: datetime = Field(..., description="Task creation timestamp")

    updated_at: datetime = Field(..., description="Last update timestamp")

    search_score: float | None = Field(
        default=None,
        description="Relevance score for search results (Elasticsearch _score)",
        examples=[1.5],
    )

    model_config = {"from_attributes": True, "use_enum_values": False}


class RecommendationResponse(BaseModel):
    """
    Response schema for personalized task recommendations.

    Includes recommendation metadata such as match score and reasoning.
    """

    task: TaskDiscoveryResponse = Field(
        ...,
        description="Recommended task details",
    )

    match_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Match score between 0 and 1 indicating recommendation confidence",
        examples=[0.85],
    )

    recommendation_reason: str = Field(
        ...,
        description="Human-readable explanation for why this task is recommended",
        examples=["Matches your interests in Instagram engagement tasks"],
    )

    factors: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured factors contributing to the recommendation",
        examples=[
            {
                "platform_affinity": 0.9,
                "task_type_preference": 0.8,
                "budget_compatibility": 0.85,
            }
        ],
    )

    model_config = {"from_attributes": True, "use_enum_values": False}
