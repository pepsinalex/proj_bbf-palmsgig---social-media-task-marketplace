"""
API Gateway Main Application.

This module provides the central FastAPI gateway with middleware, routing, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api_gateway.exceptions import (
    authentication_error_handler,
    rate_limit_error_handler,
    validation_error_handler,
)
from src.api_gateway.middleware.auth import AuthenticationMiddleware
from src.api_gateway.middleware.logging import RequestLoggingMiddleware
from src.api_gateway.middleware.rate_limit import RateLimitMiddleware
from src.api_gateway.routers.health import router as health_router
from src.shared.config import get_settings
from src.shared.database import close_database_connections
from src.shared.redis import close_redis_connections

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
        "Starting API Gateway",
        extra={
            "environment": settings.ENVIRONMENT,
            "app_name": settings.APP_NAME,
            "version": "0.1.0",
        },
    )

    try:
        # Initialize connections (lazy initialization on first use)
        logger.info("API Gateway startup complete")
        yield
    finally:
        # Shutdown
        logger.info("Shutting down API Gateway")

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
                "Error closing Redis connections", extra={"error": str(e)}, exc_info=True
            )

        logger.info("API Gateway shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Sets up middleware stack, exception handlers, and routing with proper
    configuration for CORS, authentication, rate limiting, and logging.

    Returns:
        FastAPI: Configured application instance ready for deployment
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="API Gateway for PalmsGig Social Media Task Marketplace",
        docs_url="/docs" if settings.is_development() else None,
        redoc_url="/redoc" if settings.is_development() else None,
        openapi_url="/openapi.json" if settings.is_development() else None,
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-RateLimit-Limit"],
    )

    # Add custom middleware (order matters - last added executes first)
    # 1. Request logging (innermost - executes first)
    app.add_middleware(RequestLoggingMiddleware)

    # 2. Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # 3. Authentication (outermost - executes last)
    app.add_middleware(AuthenticationMiddleware)

    # Register exception handlers
    from src.api_gateway.exceptions import (
        AuthenticationError,
        RateLimitExceeded,
        ValidationError,
    )

    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)

    # Register routers
    app.include_router(health_router, tags=["Health"])

    # API v1 routes will be added here when available
    # app.include_router(v1_router, prefix="/api/v1")

    logger.info(
        "FastAPI application configured",
        extra={
            "cors_origins": settings.CORS_ORIGINS,
            "environment": settings.ENVIRONMENT,
        },
    )

    return app


# Create application instance
app = create_application()


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint providing API information.

    Returns:
        dict: API name and version information
    """
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
    }
