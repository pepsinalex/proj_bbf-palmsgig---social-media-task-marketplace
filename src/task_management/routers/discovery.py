"""
Task Discovery API Router.

Provides REST API endpoints for task discovery, search, and personalized
recommendations with comprehensive filtering and pagination support.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_gateway.dependencies import get_current_user_id, get_database_session
from src.task_management.schemas.discovery import (
    PaginationParams,
    RecommendationResponse,
    TaskDiscoveryResponse,
    TaskFilter,
    TaskSearch,
)
from src.task_management.services.discovery_service import DiscoveryService
from src.task_management.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Task Discovery"])


def get_discovery_service(
    db: Annotated[AsyncSession, Depends(get_database_session)]
) -> DiscoveryService:
    """
    Dependency for DiscoveryService.

    Args:
        db: Database session from dependency

    Returns:
        Initialized DiscoveryService instance
    """
    return DiscoveryService(db)


def get_recommendation_service(
    db: Annotated[AsyncSession, Depends(get_database_session)]
) -> RecommendationService:
    """
    Dependency for RecommendationService.

    Args:
        db: Database session from dependency

    Returns:
        Initialized RecommendationService instance
    """
    return RecommendationService(db)


@router.get(
    "/available",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get available tasks with filtering",
    description="Retrieve available tasks with advanced filtering, sorting, and pagination",
)
async def get_available_tasks(
    discovery_service: Annotated[DiscoveryService, Depends(get_discovery_service)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of items per page"
    ),
    platform: str | None = Query(
        default=None, description="Filter by platform (instagram, facebook, etc.)"
    ),
    task_type: str | None = Query(
        default=None, description="Filter by task type (like, follow, etc.)"
    ),
    status: str | None = Query(default=None, description="Filter by task status"),
    min_budget: float | None = Query(
        default=None, ge=0, description="Minimum budget filter"
    ),
    max_budget: float | None = Query(
        default=None, ge=0, description="Maximum budget filter"
    ),
    creator_id: str | None = Query(default=None, description="Filter by creator ID"),
    exclude_expired: bool = Query(
        default=True, description="Exclude expired tasks"
    ),
    exclude_full: bool = Query(
        default=True, description="Exclude tasks at max performers"
    ),
    sort_by: str = Query(
        default="created_at",
        description="Sort field (created_at, budget, expires_at, current_performers)",
    ),
    sort_order: str = Query(default="desc", description="Sort order (asc or desc)"),
) -> dict[str, Any]:
    """
    Get available tasks with comprehensive filtering options.

    Returns paginated list of available tasks matching the filter criteria.
    """
    try:
        logger.info(
            "Received request for available tasks",
            extra={
                "page": page,
                "page_size": page_size,
                "platform": platform,
                "task_type": task_type,
            },
        )

        # Build filter object
        filters = TaskFilter(
            platform=platform,
            task_type=task_type,
            status=status,
            min_budget=min_budget,
            max_budget=max_budget,
            creator_id=creator_id,
            exclude_expired=exclude_expired,
            exclude_full=exclude_full,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Build pagination object
        pagination = PaginationParams(page=page, page_size=page_size)

        # Get tasks
        tasks, total_count = await discovery_service.get_available_tasks(
            filters=filters, pagination=pagination
        )

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size

        response = {
            "tasks": [task.model_dump() for task in tasks],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "filters_applied": filters.model_dump(exclude_none=True),
        }

        logger.info(
            "Available tasks retrieved successfully",
            extra={
                "total_count": total_count,
                "returned_count": len(tasks),
                "page": page,
            },
        )

        return response

    except ValueError as e:
        logger.warning(
            "Invalid filter parameters",
            extra={"error": str(e), "page": page, "page_size": page_size},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter parameters: {str(e)}",
        )

    except Exception as e:
        logger.error(
            "Failed to retrieve available tasks",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "page": page,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available tasks",
        )


@router.get(
    "/search",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Search tasks with full-text search",
    description="Search tasks using full-text search with filtering and pagination",
)
async def search_tasks(
    discovery_service: Annotated[DiscoveryService, Depends(get_discovery_service)],
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of items per page"
    ),
    search_fields: list[str] = Query(
        default=["title", "description", "instructions"],
        description="Fields to search in",
    ),
    platform: str | None = Query(
        default=None, description="Filter by platform (instagram, facebook, etc.)"
    ),
    task_type: str | None = Query(
        default=None, description="Filter by task type (like, follow, etc.)"
    ),
    min_budget: float | None = Query(
        default=None, ge=0, description="Minimum budget filter"
    ),
    max_budget: float | None = Query(
        default=None, ge=0, description="Maximum budget filter"
    ),
    exclude_expired: bool = Query(
        default=True, description="Exclude expired tasks"
    ),
    exclude_full: bool = Query(
        default=True, description="Exclude tasks at max performers"
    ),
    sort_by: str = Query(
        default="created_at",
        description="Sort field (created_at, budget, expires_at, current_performers)",
    ),
    sort_order: str = Query(default="desc", description="Sort order (asc or desc)"),
) -> dict[str, Any]:
    """
    Search tasks using full-text search.

    Supports searching across title, description, and instructions with
    additional filtering and pagination.
    """
    try:
        logger.info(
            "Received search request",
            extra={"query": q, "search_fields": search_fields, "page": page},
        )

        # Build search parameters
        search_params = TaskSearch(
            query=q,
            search_fields=search_fields,
        )

        # Build filter object
        filters = TaskFilter(
            platform=platform,
            task_type=task_type,
            min_budget=min_budget,
            max_budget=max_budget,
            exclude_expired=exclude_expired,
            exclude_full=exclude_full,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Build pagination object
        pagination = PaginationParams(page=page, page_size=page_size)

        # Search tasks
        tasks, total_count = await discovery_service.search_tasks(
            search_params=search_params, filters=filters, pagination=pagination
        )

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size

        response = {
            "tasks": [task.model_dump() for task in tasks],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "search_params": {
                "query": q,
                "search_fields": search_fields,
            },
            "filters_applied": filters.model_dump(exclude_none=True),
        }

        logger.info(
            "Search completed successfully",
            extra={
                "query": q,
                "total_count": total_count,
                "returned_count": len(tasks),
            },
        )

        return response

    except ValueError as e:
        logger.warning(
            "Invalid search parameters",
            extra={"error": str(e), "query": q},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {str(e)}",
        )

    except Exception as e:
        logger.error(
            "Search failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "query": q,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed",
        )


@router.get(
    "/recommended",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get personalized task recommendations",
    description="Get personalized task recommendations based on user preferences and history",
)
async def get_recommended_tasks(
    user_id: Annotated[str, Depends(get_current_user_id)],
    recommendation_service: Annotated[
        RecommendationService, Depends(get_recommendation_service)
    ],
    limit: int = Query(
        default=10, ge=1, le=50, description="Number of recommendations to return"
    ),
    min_score: float = Query(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum match score threshold (0-1)",
    ),
) -> dict[str, Any]:
    """
    Get personalized task recommendations.

    Returns tasks ranked by relevance based on user's performance history,
    platform affinity, task type preferences, and budget compatibility.

    Requires authentication.
    """
    try:
        logger.info(
            "Received recommendation request",
            extra={"user_id": user_id, "limit": limit, "min_score": min_score},
        )

        # Generate recommendations
        recommendations = await recommendation_service.generate_recommendations(
            user_id=user_id, limit=limit, min_score=min_score
        )

        response = {
            "recommendations": [rec.model_dump() for rec in recommendations],
            "total_count": len(recommendations),
            "user_id": user_id,
            "parameters": {
                "limit": limit,
                "min_score": min_score,
            },
        }

        logger.info(
            "Recommendations generated successfully",
            extra={
                "user_id": user_id,
                "recommendation_count": len(recommendations),
                "avg_score": (
                    sum(r.match_score for r in recommendations) / len(recommendations)
                    if recommendations
                    else 0
                ),
            },
        )

        return response

    except Exception as e:
        logger.error(
            "Failed to generate recommendations",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task details by ID",
    description="Retrieve detailed information about a specific task",
)
async def get_task_details(
    task_id: str,
    discovery_service: Annotated[DiscoveryService, Depends(get_discovery_service)],
) -> TaskDiscoveryResponse:
    """
    Get detailed information about a specific task.

    Returns complete task details including budget, performers, and metadata.
    """
    try:
        logger.info("Received request for task details", extra={"task_id": task_id})

        task = await discovery_service.get_task_by_id(task_id)

        if not task:
            logger.warning("Task not found", extra={"task_id": task_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found",
            )

        logger.info("Task details retrieved successfully", extra={"task_id": task_id})

        return task

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "Failed to retrieve task details",
            extra={
                "task_id": task_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task details",
        )
