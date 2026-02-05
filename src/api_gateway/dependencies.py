"""
FastAPI Dependency Injection Functions for API Gateway.

This module provides reusable dependency functions for database sessions,
Redis clients, authentication, and configuration access.
"""

import logging
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import Settings, get_settings
from src.shared.database import get_db_session
from src.shared.redis import get_redis_client

logger = logging.getLogger(__name__)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting a database session.

    Provides an async database session with automatic cleanup.
    Handles errors and ensures proper session closure.

    Yields:
        AsyncSession: SQLAlchemy async database session

    Raises:
        HTTPException: If database connection fails
    """
    try:
        async for session in get_db_session():
            yield session
    except Exception as e:
        logger.error(
            "Failed to get database session",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )


async def get_redis() -> AsyncGenerator:
    """
    Dependency for getting a Redis client.

    Provides a Redis client for caching and rate limiting operations.
    Handles connection errors gracefully.

    Yields:
        Redis client instance

    Raises:
        HTTPException: If Redis connection fails
    """
    try:
        redis_client = await get_redis_client()
        yield redis_client
    except Exception as e:
        logger.error(
            "Failed to get Redis client",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection failed",
        )


def get_current_user(request: Request) -> Optional[dict]:
    """
    Dependency for getting the current authenticated user.

    Extracts user information from request state (set by auth middleware).
    Returns None if user is not authenticated.

    Args:
        request: FastAPI request object

    Returns:
        Optional[dict]: User information dict or None if not authenticated
    """
    user = getattr(request.state, "user", None)
    return user


def get_current_user_id(request: Request) -> Optional[str]:
    """
    Dependency for getting the current user ID.

    Extracts user ID from request state (set by auth middleware).
    Returns None if user is not authenticated.

    Args:
        request: FastAPI request object

    Returns:
        Optional[str]: User ID or None if not authenticated
    """
    user_id = getattr(request.state, "user_id", None)
    return user_id


def require_authentication(request: Request) -> str:
    """
    Dependency that requires authentication.

    Ensures the request is authenticated and returns user ID.
    Raises 401 error if not authenticated.

    Args:
        request: FastAPI request object

    Returns:
        str: Authenticated user ID

    Raises:
        HTTPException: If user is not authenticated
    """
    is_authenticated = getattr(request.state, "is_authenticated", False)

    if not is_authenticated:
        logger.warning(
            "Unauthenticated access attempt",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        logger.error(
            "Authentication state inconsistent - missing user_id",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


def is_authenticated(request: Request) -> bool:
    """
    Dependency for checking if request is authenticated.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if authenticated, False otherwise
    """
    return getattr(request.state, "is_authenticated", False)


def get_correlation_id(request: Request) -> str:
    """
    Dependency for getting the request correlation ID.

    Extracts correlation ID from request state (set by logging middleware).
    Returns "unknown" if not found (shouldn't happen in normal operation).

    Args:
        request: FastAPI request object

    Returns:
        str: Correlation ID for the request
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return correlation_id


def get_app_settings() -> Settings:
    """
    Dependency for getting application settings.

    Provides access to the application configuration.

    Returns:
        Settings: Application settings instance
    """
    return get_settings()
