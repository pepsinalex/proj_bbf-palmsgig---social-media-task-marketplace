"""
Request/Response Logging Middleware for API Gateway.

This module provides comprehensive request and response logging with correlation IDs
for distributed tracing and observability.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses with correlation IDs.

    Generates unique correlation IDs for each request, logs request/response details,
    and adds correlation ID to response headers for distributed tracing.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request with logging and correlation ID tracking.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: HTTP response with correlation ID header
        """
        # Generate correlation ID
        correlation_id = self._get_or_create_correlation_id(request)

        # Set correlation ID in request state
        request.state.correlation_id = correlation_id

        # Start timing
        start_time = time.time()

        # Log incoming request
        self._log_request(request, correlation_id)

        # Process request
        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log response
            self._log_response(request, response, correlation_id, duration)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = correlation_id

            return response

        except Exception as e:
            # Log error
            duration = time.time() - start_time

            logger.error(
                "Request processing error",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            raise

    def _get_or_create_correlation_id(self, request: Request) -> str:
        """
        Get existing correlation ID from headers or create a new one.

        Args:
            request: Incoming HTTP request

        Returns:
            str: Correlation ID for the request
        """
        # Check for existing correlation ID in headers
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            correlation_id = request.headers.get("X-Request-ID")

        if not correlation_id:
            # Generate new correlation ID
            correlation_id = str(uuid.uuid4())

        return correlation_id

    def _log_request(self, request: Request, correlation_id: str) -> None:
        """
        Log incoming request details.

        Args:
            request: Incoming HTTP request
            correlation_id: Correlation ID for the request
        """
        # Get user information if available
        user_id = getattr(request.state, "user_id", None)
        is_authenticated = getattr(request.state, "is_authenticated", False)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            "Incoming request",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "user_id": user_id,
                "is_authenticated": is_authenticated,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent"),
            },
        )

    def _log_response(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        duration: float,
    ) -> None:
        """
        Log outgoing response details.

        Args:
            request: Original HTTP request
            response: HTTP response
            correlation_id: Correlation ID for the request
            duration: Request processing duration in seconds
        """
        # Get user information if available
        user_id = getattr(request.state, "user_id", None)

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        logger.log(
            log_level,
            "Outgoing response",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": round(duration, 3),
                "duration_ms": round(duration * 1000, 2),
                "user_id": user_id,
            },
        )
