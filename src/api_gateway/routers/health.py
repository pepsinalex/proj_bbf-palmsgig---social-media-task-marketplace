"""
Health Check Router for API Gateway.

This module provides health check endpoints for monitoring, load balancing,
and observability of the API Gateway service.
"""

import logging
from typing import Any

from fastapi import APIRouter, Response, status

from src.shared.config import get_settings
from src.shared.database import check_database_health
from src.shared.redis import check_redis_health

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """
    Basic liveness probe.

    Returns a simple OK response to indicate the service is running.
    Used by orchestrators like Kubernetes for liveness checks.

    Returns:
        dict: Status indicating service is alive
    """
    return {"status": "ok", "service": "api_gateway"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness probe with dependency health checks.

    Checks connectivity to critical dependencies (database and Redis).
    Used by load balancers to determine if the service can handle traffic.

    Args:
        response: FastAPI response object for setting status code

    Returns:
        dict: Detailed health status of service and dependencies
    """
    health_status = {
        "status": "ready",
        "service": "api_gateway",
        "dependencies": {},
    }

    all_healthy = True

    # Check database connectivity
    try:
        db_healthy = await check_database_health()
        health_status["dependencies"]["database"] = (
            "healthy" if db_healthy else "unhealthy"
        )
        if not db_healthy:
            all_healthy = False
            logger.warning("Database health check failed")
    except Exception as e:
        health_status["dependencies"]["database"] = "unhealthy"
        all_healthy = False
        logger.error(
            "Database health check error",
            extra={"error": str(e)},
            exc_info=True,
        )

    # Check Redis connectivity
    try:
        redis_healthy = await check_redis_health()
        health_status["dependencies"]["redis"] = (
            "healthy" if redis_healthy else "unhealthy"
        )
        if not redis_healthy:
            all_healthy = False
            logger.warning("Redis health check failed")
    except Exception as e:
        health_status["dependencies"]["redis"] = "unhealthy"
        all_healthy = False
        logger.error(
            "Redis health check error",
            extra={"error": str(e)},
            exc_info=True,
        )

    # Set overall status and HTTP status code
    if not all_healthy:
        health_status["status"] = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(
            "Service readiness check failed",
            extra={"health_status": health_status},
        )

    return health_status


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics() -> dict[str, Any]:
    """
    Basic metrics endpoint.

    Provides simple metrics about the service for monitoring.
    Can be extended to include Prometheus-style metrics.

    Returns:
        dict: Basic service metrics
    """
    metrics_data = {
        "service": "api_gateway",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }

    # Add database connectivity metric
    try:
        db_healthy = await check_database_health()
        metrics_data["database_connected"] = db_healthy
    except Exception:
        metrics_data["database_connected"] = False

    # Add Redis connectivity metric
    try:
        redis_healthy = await check_redis_health()
        metrics_data["redis_connected"] = redis_healthy
    except Exception:
        metrics_data["redis_connected"] = False

    return metrics_data
