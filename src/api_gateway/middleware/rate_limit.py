"""
Rate Limiting Middleware for API Gateway.

This module provides Redis-based sliding window rate limiting to protect the API
from abuse and ensure fair resource usage across clients.
"""

import logging
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.shared.redis import get_redis_client

logger = logging.getLogger(__name__)

# Default rate limit configuration
DEFAULT_RATE_LIMIT = 100  # requests per window
DEFAULT_WINDOW_SECONDS = 60  # 1 minute window

# Public paths that don't have rate limiting
PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/metrics",
}


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window} seconds. "
            f"Retry after {retry_after} seconds."
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based sliding window rate limiting middleware.

    Implements rate limiting using Redis with per-user and per-IP tracking.
    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(
        self,
        app,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
            rate_limit: Maximum number of requests allowed per window
            window_seconds: Time window in seconds for rate limiting
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: HTTP response with rate limit headers
        """
        # Skip rate limiting for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Get identifier for rate limiting (user_id or IP)
        identifier = self._get_identifier(request)

        try:
            # Check and update rate limit
            allowed, remaining, reset_time = await self._check_rate_limit(identifier)

            if not allowed:
                # Rate limit exceeded
                retry_after = max(1, int(reset_time - time.time()))

                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "identifier": identifier,
                        "path": request.url.path,
                        "method": request.method,
                        "retry_after": retry_after,
                    },
                )

                # Create 429 response
                response = Response(
                    content='{"detail": "Rate limit exceeded. Too many requests."}',
                    status_code=429,
                    media_type="application/json",
                )

                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(reset_time))
                response.headers["Retry-After"] = str(retry_after)

                return response

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful response
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))

            return response

        except Exception as e:
            # Log error but don't block request if rate limiting fails
            logger.error(
                "Rate limiting error - allowing request",
                extra={
                    "identifier": identifier,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Allow request to proceed
            return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """
        Check if the request path is public and doesn't require rate limiting.

        Args:
            path: Request URL path

        Returns:
            bool: True if path is public, False otherwise
        """
        return path in PUBLIC_PATHS

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Uses user_id if authenticated, otherwise falls back to IP address.

        Args:
            request: Incoming HTTP request

        Returns:
            str: Unique identifier for rate limiting
        """
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)

        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _check_rate_limit(
        self, identifier: str
    ) -> tuple[bool, int, float]:
        """
        Check and update rate limit using Redis sliding window.

        Args:
            identifier: Unique identifier for the client

        Returns:
            tuple: (allowed, remaining_requests, reset_time)
        """
        redis_client = await get_redis_client()
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Redis key for this identifier
        key = f"rate_limit:{identifier}"

        try:
            # Remove old entries outside the window
            await redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = await redis_client.zcard(key)

            if request_count >= self.rate_limit:
                # Rate limit exceeded
                # Get oldest request time to calculate reset
                oldest_requests = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_requests:
                    oldest_time = oldest_requests[0][1]
                    reset_time = oldest_time + self.window_seconds
                else:
                    reset_time = current_time + self.window_seconds

                return False, 0, reset_time

            # Add current request to the window
            await redis_client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            await redis_client.expire(key, self.window_seconds + 1)

            # Calculate remaining requests
            remaining = self.rate_limit - request_count - 1

            # Calculate reset time (end of current window)
            reset_time = current_time + self.window_seconds

            logger.debug(
                "Rate limit check passed",
                extra={
                    "identifier": identifier,
                    "request_count": request_count + 1,
                    "remaining": remaining,
                    "limit": self.rate_limit,
                },
            )

            return True, remaining, reset_time

        except Exception as e:
            logger.error(
                "Redis rate limit check failed",
                extra={
                    "identifier": identifier,
                    "error": str(e),
                },
                exc_info=True,
            )
            # On error, allow the request (fail open)
            return True, self.rate_limit - 1, current_time + self.window_seconds
