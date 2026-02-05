"""
Authentication Middleware for API Gateway.

This module provides JWT token validation middleware that authenticates requests
and extracts user information from JWT tokens.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware for validating and extracting user information.

    This middleware validates JWT tokens in the Authorization header, extracts user
    information, and sets it in the request state. Public endpoints are skipped.
    """

    def __init__(self, app, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application instance
            redis_client: Optional Redis client for token blacklist checking
        """
        super().__init__(app)
        self.redis = redis_client

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request with JWT authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler

        Returns:
            Response: HTTP response from downstream handler
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract and validate JWT token
        token = self._extract_token(request)

        if token:
            user_info = await self._decode_and_validate_token(token)
            if user_info:
                # Set user information in request state
                request.state.user = user_info
                request.state.user_id = user_info.get("sub")
                request.state.is_authenticated = True

                logger.debug(
                    "Request authenticated",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "user_id": request.state.user_id,
                    },
                )
            else:
                # Invalid token - set unauthenticated state
                request.state.user = None
                request.state.user_id = None
                request.state.is_authenticated = False
        else:
            # No token provided - set unauthenticated state
            request.state.user = None
            request.state.user_id = None
            request.state.is_authenticated = False

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """
        Check if the request path is public and doesn't require authentication.

        Args:
            path: Request URL path

        Returns:
            bool: True if path is public, False otherwise
        """
        # Check exact matches
        if path in PUBLIC_PATHS:
            return True

        # Check path prefixes for docs
        if path.startswith(("/docs", "/redoc", "/openapi.json")):
            return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.

        Args:
            request: Incoming HTTP request

        Returns:
            Optional[str]: JWT token if present and valid format, None otherwise
        """
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        # Expected format: "Bearer <token>"
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(
                "Invalid Authorization header format",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            return None

        return parts[1]

    def _decode_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            Optional[dict]: Decoded token payload if valid, None otherwise
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )

            # Token is valid - return payload
            logger.debug(
                "JWT token decoded successfully",
                extra={
                    "user_id": payload.get("sub"),
                    "exp": payload.get("exp"),
                },
            )

            return payload

        except JWTError as e:
            # Token is invalid or expired
            logger.warning(
                "JWT token validation failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None
        except Exception as e:
            # Unexpected error during token validation
            logger.error(
                "Unexpected error during JWT token validation",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    async def _decode_and_validate_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate JWT token with blacklist checking.

        Args:
            token: JWT token string

        Returns:
            Optional[dict]: Decoded token payload if valid and not blacklisted, None otherwise
        """
        payload = self._decode_token(token)
        if not payload:
            return None

        if self.redis:
            try:
                jti = payload.get("jti")
                if jti:
                    blacklist_key = f"token:blacklist:{jti}"
                    is_blacklisted = await self.redis.exists(blacklist_key)

                    if is_blacklisted:
                        logger.warning(
                            "Token is blacklisted",
                            extra={
                                "jti": jti,
                                "user_id": payload.get("sub"),
                            },
                        )
                        return None

            except Exception as e:
                logger.error(
                    "Failed to check token blacklist",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        return payload
