"""
Base platform client with common functionality.

This module provides an abstract base class for platform-specific API clients,
including rate limiting, error handling, token management, and common API operations.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import httpx

from src.shared.config import get_settings
from src.social_media.enums.platform_enums import Platform, get_platform_config

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None) -> None:
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets
        """
        super().__init__(message)
        self.retry_after = retry_after


class PlatformAPIError(Exception):
    """Exception raised for platform API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None,
    ) -> None:
        """
        Initialize platform API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from API
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BaseClient(ABC):
    """
    Abstract base client for social media platform APIs.

    Provides common functionality including:
    - HTTP client management
    - Rate limiting
    - Error handling
    - Token management
    - Retry logic
    - Request logging

    Subclasses must implement platform-specific methods.
    """

    def __init__(self, platform: Platform, access_token: str) -> None:
        """
        Initialize base platform client.

        Args:
            platform: Social media platform
            access_token: OAuth access token for API authentication
        """
        self.platform = platform
        self.access_token = access_token
        self.config = get_platform_config(platform)
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._rate_limit_remaining = self.config.rate_limit_requests
        self._rate_limit_reset_at: Optional[datetime] = None

        logger.info(
            "Platform client initialized",
            extra={
                "platform": platform.value,
                "api_base_url": self.config.api_base_url,
            },
        )

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self.http_client.aclose()
        logger.debug("Platform client closed", extra={"platform": self.platform.value})

    def _update_rate_limit(self, response: httpx.Response) -> None:
        """
        Update rate limit state from response headers.

        Args:
            response: HTTP response with rate limit headers
        """
        try:
            remaining_header = response.headers.get(
                "X-Rate-Limit-Remaining", response.headers.get("x-ratelimit-remaining")
            )
            if remaining_header:
                self._rate_limit_remaining = int(remaining_header)

            reset_header = response.headers.get(
                "X-Rate-Limit-Reset", response.headers.get("x-ratelimit-reset")
            )
            if reset_header:
                reset_timestamp = int(reset_header)
                self._rate_limit_reset_at = datetime.fromtimestamp(reset_timestamp)

            logger.debug(
                "Rate limit updated",
                extra={
                    "platform": self.platform.value,
                    "remaining": self._rate_limit_remaining,
                    "reset_at": self._rate_limit_reset_at.isoformat()
                    if self._rate_limit_reset_at
                    else None,
                },
            )
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Failed to parse rate limit headers",
                extra={
                    "platform": self.platform.value,
                    "error": str(exc),
                },
            )

    def _check_rate_limit(self) -> None:
        """
        Check if rate limit allows request.

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if self._rate_limit_remaining <= 0:
            if self._rate_limit_reset_at and self._rate_limit_reset_at > datetime.utcnow():
                retry_after = int((self._rate_limit_reset_at - datetime.utcnow()).total_seconds())
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "platform": self.platform.value,
                        "retry_after": retry_after,
                    },
                )
                raise RateLimitError(
                    f"Rate limit exceeded for {self.platform.value}",
                    retry_after=retry_after,
                )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> dict[str, Any]:
        """
        Make HTTP request with error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json: JSON body data
            headers: Additional headers
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff delay in seconds

        Returns:
            Response data as dictionary

        Raises:
            RateLimitError: If rate limit is exceeded
            PlatformAPIError: If API request fails
        """
        self._check_rate_limit()

        url = f"{self.config.api_base_url}/{endpoint.lstrip('/')}"

        request_headers = dict(self.http_client.headers)
        if headers:
            request_headers.update(headers)

        last_exception = None

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                response = await self.http_client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=request_headers,
                )

                duration = time.time() - start_time

                self._update_rate_limit(response)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "Rate limit hit",
                        extra={
                            "platform": self.platform.value,
                            "endpoint": endpoint,
                            "retry_after": retry_after,
                        },
                    )
                    raise RateLimitError(
                        f"Rate limit exceeded for {endpoint}",
                        retry_after=retry_after,
                    )

                if response.status_code >= 500:
                    logger.error(
                        "Server error from platform API",
                        extra={
                            "platform": self.platform.value,
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_backoff * (2**attempt))
                        continue
                    raise PlatformAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()

                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"text": response.text}

                logger.info(
                    "API request successful",
                    extra={
                        "platform": self.platform.value,
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "duration_ms": int(duration * 1000),
                    },
                )

                return response_data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error from platform API",
                    extra={
                        "platform": self.platform.value,
                        "endpoint": endpoint,
                        "status_code": exc.response.status_code,
                        "response": exc.response.text[:500],
                    },
                )
                try:
                    error_data = exc.response.json()
                except Exception:
                    error_data = {"text": exc.response.text}

                raise PlatformAPIError(
                    f"API request failed: {exc.response.status_code}",
                    status_code=exc.response.status_code,
                    response_data=error_data,
                ) from exc

            except RateLimitError:
                raise

            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Request attempt failed",
                    extra={
                        "platform": self.platform.value,
                        "endpoint": endpoint,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_backoff * (2**attempt))
                    continue
                break

        logger.error(
            "All retry attempts failed",
            extra={
                "platform": self.platform.value,
                "endpoint": endpoint,
                "max_retries": max_retries,
            },
        )
        raise PlatformAPIError(
            f"Request failed after {max_retries} attempts: {str(last_exception)}"
        ) from last_exception

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make GET request to platform API.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            **kwargs: Additional arguments for _make_request

        Returns:
            Response data as dictionary
        """
        return await self._make_request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make POST request to platform API.

        Args:
            endpoint: API endpoint path
            data: Form data
            json: JSON body data
            **kwargs: Additional arguments for _make_request

        Returns:
            Response data as dictionary
        """
        return await self._make_request("POST", endpoint, data=data, json=json, **kwargs)

    @abstractmethod
    async def get_user_profile(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get user profile information.

        Args:
            user_id: User ID (uses authenticated user if None)

        Returns:
            User profile data
        """
        pass

    @abstractmethod
    async def verify_account_ownership(self, account_id: str) -> bool:
        """
        Verify that the authenticated user owns the specified account.

        Args:
            account_id: Platform-specific account ID

        Returns:
            True if ownership is verified
        """
        pass

    def update_access_token(self, access_token: str) -> None:
        """
        Update access token for authentication.

        Args:
            access_token: New OAuth access token
        """
        self.access_token = access_token
        self.http_client.headers["Authorization"] = f"Bearer {access_token}"
        logger.info(
            "Access token updated",
            extra={"platform": self.platform.value},
        )
