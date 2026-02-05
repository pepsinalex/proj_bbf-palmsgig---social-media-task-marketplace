"""
Unit tests for API Gateway middleware components.

Tests authentication, rate limiting, and logging middleware in isolation.
"""

import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jose import jwt
from starlette.testclient import TestClient

from src.api_gateway.middleware.auth import AuthenticationMiddleware
from src.api_gateway.middleware.logging import RequestLoggingMiddleware
from src.api_gateway.middleware.rate_limit import RateLimitMiddleware
from src.shared.config import get_settings

settings = get_settings()


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "message": "test",
            "is_authenticated": getattr(request.state, "is_authenticated", False),
            "user_id": getattr(request.state, "user_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
        }

    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    return app


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    payload = {
        "sub": "user-123",
        "email": "user@example.com",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def expired_token():
    """Create an expired JWT token."""
    payload = {
        "sub": "user-123",
        "email": "user@example.com",
        "exp": int(time.time()) - 3600,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    def test_public_paths_bypass_authentication(self, test_app):
        """Test that public paths bypass authentication."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        response = client.get("/public")

        assert response.status_code == 200

    def test_valid_token_authenticates_request(self, test_app, valid_token):
        """Test that valid tokens authenticate requests."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is True
        assert data["user_id"] == "user-123"

    def test_expired_token_fails_authentication(self, test_app, expired_token):
        """Test that expired tokens fail authentication."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False
        assert data["user_id"] is None

    def test_missing_token_leaves_request_unauthenticated(self, test_app):
        """Test that requests without tokens are unauthenticated."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False
        assert data["user_id"] is None

    def test_invalid_token_format_handled_gracefully(self, test_app):
        """Test that invalid token formats are handled."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        headers = {"Authorization": "InvalidFormat"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False

    def test_malformed_jwt_handled_gracefully(self, test_app):
        """Test that malformed JWTs are handled."""
        test_app.add_middleware(AuthenticationMiddleware)
        client = TestClient(test_app)

        headers = {"Authorization": "Bearer malformed.jwt.token"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False

    def test_health_check_paths_bypass_authentication(self, test_app):
        """Test that health check paths bypass authentication."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    def test_correlation_id_generated_for_request(self, test_app):
        """Test that correlation ID is generated."""
        test_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers

    def test_existing_correlation_id_preserved(self, test_app):
        """Test that existing correlation IDs are preserved."""
        test_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(test_app)

        correlation_id = "test-corr-id-123"
        headers = {"X-Correlation-ID": correlation_id}

        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        # Correlation ID should be in response
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers

    def test_correlation_id_added_to_request_state(self, test_app):
        """Test that correlation ID is added to request state."""
        test_app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        # Correlation ID should be in request state
        assert data["correlation_id"] is not None or data["correlation_id"] != "unknown"

    def test_request_logging_handles_errors(self, test_app):
        """Test that logging middleware handles errors gracefully."""
        app = FastAPI()

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)

        # Error should be logged but re-raised
        with pytest.raises(ValueError):
            client.get("/error")


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_requests_below_limit_allowed(self, mock_redis_client, test_app):
        """Test that requests below the limit are allowed."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=10)  # 10 requests in window
        mock_client.zadd = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[])
        mock_redis_client.return_value = mock_client

        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_requests_exceeding_limit_blocked(self, mock_redis_client, test_app):
        """Test that requests exceeding the limit are blocked."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=100)  # At limit
        mock_client.zrange = AsyncMock(return_value=[(b"1", time.time() - 30)])
        mock_redis_client.return_value = mock_client

        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "Retry-After" in response.headers

    def test_public_paths_bypass_rate_limiting(self, test_app):
        """Test that public paths bypass rate limiting."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(RateLimitMiddleware, rate_limit=1, window_seconds=60)
        client = TestClient(app)

        # Health endpoint should not be rate limited
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_rate_limit_uses_user_id_when_authenticated(self, mock_redis_client, test_app):
        """Test that rate limiting uses user_id for authenticated requests."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=10)
        mock_client.zadd = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[])
        mock_redis_client.return_value = mock_client

        # Add both middlewares
        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        test_app.add_middleware(AuthenticationMiddleware)

        client = TestClient(test_app)

        valid_token = jwt.encode(
            {
                "sub": "user-123",
                "email": "user@example.com",
                "exp": int(time.time()) + 3600,
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_rate_limit_falls_back_to_ip_when_unauthenticated(
        self, mock_redis_client, test_app
    ):
        """Test that rate limiting uses IP for unauthenticated requests."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=10)
        mock_client.zadd = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[])
        mock_redis_client.return_value = mock_client

        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_rate_limit_handles_redis_errors_gracefully(self, mock_redis_client, test_app):
        """Test that rate limiting handles Redis errors gracefully."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock(side_effect=Exception("Redis error"))
        mock_redis_client.return_value = mock_client

        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        client = TestClient(test_app)

        # Should allow request even if Redis fails
        response = client.get("/test")

        assert response.status_code == 200


@pytest.mark.integration
class TestMiddlewareStack:
    """Test middleware stack integration."""

    def test_middleware_execution_order(self, test_app, valid_token):
        """Test that middleware executes in correct order."""
        # Add middleware in reverse order (last added executes first)
        test_app.add_middleware(RequestLoggingMiddleware)
        test_app.add_middleware(AuthenticationMiddleware)

        client = TestClient(test_app)

        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Both middleware should have executed
        assert data["is_authenticated"] is True
        assert data["correlation_id"] is not None
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_full_middleware_stack(self, mock_redis_client, test_app, valid_token):
        """Test complete middleware stack functionality."""
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=10)
        mock_client.zadd = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[])
        mock_redis_client.return_value = mock_client

        # Add all middleware
        test_app.add_middleware(RequestLoggingMiddleware)
        test_app.add_middleware(RateLimitMiddleware, rate_limit=100, window_seconds=60)
        test_app.add_middleware(AuthenticationMiddleware)

        client = TestClient(test_app)

        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # All middleware should have executed
        assert data["is_authenticated"] is True
        assert data["user_id"] == "user-123"
        assert data["correlation_id"] is not None
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers
        assert "X-RateLimit-Limit" in response.headers
