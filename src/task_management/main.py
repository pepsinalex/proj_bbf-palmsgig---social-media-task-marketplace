"""
Task Management Service Main Application.

This module provides the FastAPI application for the task management service
with routing, middleware, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api_gateway.middleware.auth import AuthenticationMiddleware
from src.api_gateway.middleware.logging import RequestLoggingMiddleware
from src.shared.config import get_settings
from src.shared.database import check_database_health, close_database_connections
from src.shared.redis import check_redis_health, close_redis_connections
from src.task_management.routers import tasks_router
from src.task_management.routers.task_creation import router as task_creation_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager for startup and shutdown events.

    Handles initialization and cleanup of application resources including
    database connections, Redis connections, and other dependencies.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info(
        "Starting Task Management Service",
        extra={
            "environment": settings.ENVIRONMENT,
            "app_name": "Task Management Service",
            "version": "0.1.0",
        },
    )

    try:
        # Check database connectivity
        db_healthy = await check_database_health()
        if not db_healthy:
            logger.error("Database health check failed on startup")
        else:
            logger.info("Database connection verified")

        # Check Redis connectivity
        redis_healthy = await check_redis_health()
        if not redis_healthy:
            logger.warning("Redis health check failed on startup")
        else:
            logger.info("Redis connection verified")

        logger.info("Task Management Service startup complete")
        yield
    finally:
        # Shutdown
        logger.info("Shutting down Task Management Service")

        try:
            await close_database_connections()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(
                "Error closing database connections",
                extra={"error": str(e)},
                exc_info=True,
            )

        try:
            await close_redis_connections()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(
                "Error closing Redis connections",
                extra={"error": str(e)},
                exc_info=True,
            )

        logger.info("Task Management Service shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Sets up middleware stack, exception handlers, and routing with proper
    configuration for CORS, authentication, logging, and health checks.

    Returns:
        FastAPI: Configured application instance ready for deployment
    """
    app = FastAPI(
        title="Task Management Service",
        version="0.1.0",
        description="Task Management Service for PalmsGig Social Media Task Marketplace",
        docs_url="/docs" if settings.is_development() else None,
        redoc_url="/redoc" if settings.is_development() else None,
        openapi_url="/openapi.json" if settings.is_development() else None,
        lifespan=lifespan,
    )

    # CORS Middleware
    cors_origins = settings.parse_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Authentication Middleware
    app.add_middleware(AuthenticationMiddleware)

    # Exception Handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError exceptions."""
        logger.warning(
            "Validation error",
            extra={"path": request.url.path, "error": str(exc)},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # Health Check Endpoint
    @app.get(
        "/health",
        tags=["health"],
        summary="Service health check",
        description="Check if the service is running and responsive",
    )
    async def health_check() -> dict[str, str]:
        """
        Health check endpoint.

        Returns:
            Service status
        """
        return {"status": "healthy", "service": "task_management"}

    # Readiness Check Endpoint
    @app.get(
        "/ready",
        tags=["health"],
        summary="Service readiness check",
        description="Check if the service is ready to accept requests",
    )
    async def readiness_check() -> dict[str, str | bool]:
        """
        Readiness check endpoint.

        Verifies database and Redis connectivity.

        Returns:
            Readiness status with dependencies
        """
        db_healthy = await check_database_health()
        redis_healthy = await check_redis_health()

        all_healthy = db_healthy and redis_healthy

        return {
            "status": "ready" if all_healthy else "not ready",
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        }

    # Root Endpoint
    @app.get(
        "/",
        tags=["root"],
        summary="Service information",
        description="Get service information and version",
    )
    async def root() -> dict[str, str]:
        """
        Root endpoint.

        Returns:
            Service information
        """
        return {
            "service": "Task Management Service",
            "version": "0.1.0",
            "status": "running",
        }

    # Include Routers
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(task_creation_router, prefix="/api/v1")

    logger.info(
        "Task Management Service application configured",
        extra={"cors_origins": cors_origins},
    )

    return app


# Create application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.task_management.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development(),
        log_level=settings.LOG_LEVEL.lower(),
    )
