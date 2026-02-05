"""
Custom Exception Handlers for API Gateway.

This module provides custom exceptions and exception handlers for consistent
error responses across the API Gateway.
"""

import logging
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed", **context):
        self.message = message
        self.context = context
        super().__init__(self.message)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int = 0,
        retry_after: int = 0,
        **context,
    ):
        self.message = message
        self.limit = limit
        self.retry_after = retry_after
        self.context = context
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for validation errors."""

    def __init__(self, message: str = "Validation error", errors: list = None, **context):
        self.message = message
        self.errors = errors or []
        self.context = context
        super().__init__(self.message)


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """
    Handle authentication errors with consistent error response.

    Args:
        request: FastAPI request object
        exc: Authentication exception

    Returns:
        JSONResponse: Standardized error response
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.warning(
        "Authentication error",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "error": exc.message,
            "context": exc.context,
        },
    )

    error_response: dict[str, Any] = {
        "error": "authentication_failed",
        "message": exc.message,
        "correlation_id": correlation_id,
    }

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_response,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def rate_limit_error_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Handle rate limit exceeded errors with retry information.

    Args:
        request: FastAPI request object
        exc: Rate limit exception

    Returns:
        JSONResponse: Standardized error response with rate limit headers
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.warning(
        "Rate limit exceeded",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "limit": exc.limit,
            "retry_after": exc.retry_after,
        },
    )

    error_response: dict[str, Any] = {
        "error": "rate_limit_exceeded",
        "message": exc.message,
        "correlation_id": correlation_id,
        "retry_after": exc.retry_after,
    }

    headers = {}
    if exc.limit > 0:
        headers["X-RateLimit-Limit"] = str(exc.limit)
        headers["X-RateLimit-Remaining"] = "0"

    if exc.retry_after > 0:
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response,
        headers=headers,
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Handle validation errors with detailed error information.

    Args:
        request: FastAPI request object
        exc: Validation exception

    Returns:
        JSONResponse: Standardized error response with validation details
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.warning(
        "Validation error",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "error": exc.message,
            "errors": exc.errors,
        },
    )

    error_response: dict[str, Any] = {
        "error": "validation_error",
        "message": exc.message,
        "correlation_id": correlation_id,
    }

    if exc.errors:
        error_response["details"] = exc.errors

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )
