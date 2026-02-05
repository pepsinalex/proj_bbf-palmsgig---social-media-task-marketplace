"""
Social Media Integration Service Main Application.

This module provides the FastAPI application for the social media integration service
with OAuth 2.0 implementation, routing, middleware, and lifecycle management.
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
from src.social_media.routers.social_accounts import router as social_accounts_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager for startup and shutdown events.

    Handles initialization and cleanup of application resources including
    database connections, Redis connections, OAuth client initialization,
    and platform client setup.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info(
        "Starting Social Media Integration Service",
        extra={
            "environment": settings.ENVIRONMENT,
            "app_name": "Social Media Integration Service",
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

        # Validate OAuth configuration
        try:
            from src.social_media.enums.platform_enums import PLATFORM_CONFIGS, Platform

            configured_platforms = list(PLATFORM_CONFIGS.keys())
            logger.info(
                "OAuth platform configurations loaded",
                extra={
                    "platforms": [p.value for p in configured_platforms],
                    "count": len(configured_platforms),
                },
            )
        except Exception as e:
            logger.error(
                "Failed to load platform configurations",
                extra={"error": str(e)},
                exc_info=True,
            )

        logger.info("Social Media Integration Service startup complete")
        yield
    finally:
        # Shutdown
        logger.info("Shutting down Social Media Integration Service")

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

        logger.info("Social Media Integration Service shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Sets up middleware stack, exception handlers, OAuth configuration,
    and routing with proper configuration for CORS, authentication,
    logging, and health checks.

    Returns:
        FastAPI: Configured application instance ready for deployment
    """
    app = FastAPI(
        title="Social Media Integration Service",
        version="0.1.0",
        description="Social Media Integration Service for PalmsGig - OAuth 2.0 implementation for major social platforms",
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
        """
        Handle ValueError exceptions.

        Args:
            request: FastAPI request
            exc: ValueError exception

        Returns:
            JSON error response
        """
        logger.warning(
            "Validation error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
            },
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Handle unexpected exceptions.

        Args:
            request: FastAPI request
            exc: Exception

        Returns:
            JSON error response
        """
        logger.error(
            "Unexpected error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__,
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
        return {"status": "healthy", "service": "social_media"}

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
            "service": "Social Media Integration Service",
            "version": "0.1.0",
            "status": "running",
        }

    # Platforms Information Endpoint
    @app.get(
        "/platforms",
        tags=["platforms"],
        summary="List supported platforms",
        description="Get list of supported social media platforms",
    )
    async def list_platforms() -> dict[str, list[dict[str, str]]]:
        """
        List supported social media platforms.

        Returns:
            List of platform information
        """
        from src.social_media.enums.platform_enums import PLATFORM_CONFIGS

        platforms = [
            {
                "platform": config.platform.value,
                "display_name": config.platform.display_name,
                "supports_refresh_token": config.supports_refresh_token,
            }
            for config in PLATFORM_CONFIGS.values()
        ]

        logger.debug(
            "Platforms list requested",
            extra={"count": len(platforms)},
        )

        return {"platforms": platforms}

    # Include Routers
    app.include_router(social_accounts_router, prefix="/api/v1")

    logger.info(
        "Social Media Integration Service application configured",
        extra={
            "cors_origins": cors_origins,
            "routes_count": len(app.routes),
        },
    )

    return app


# Create application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.social_media.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.is_development(),
        log_level=settings.LOG_LEVEL.lower(),
    )
