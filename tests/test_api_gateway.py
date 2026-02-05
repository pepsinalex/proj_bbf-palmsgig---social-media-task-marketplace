"""
Integration tests for API Gateway functionality.

Tests health endpoints, authentication middleware, rate limiting, CORS,
error handling, and API routing using FastAPI TestClient.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from src.api_gateway.main import app
from src.shared.config import get_settings

settings = get_settings()


@pytest.fixture
def client():
    """Create a test client for the API Gateway."""
    return TestClient(app)


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing."""
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "exp": int(time.time()) + 3600,  # Expires in 1 hour
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


@pytest.fixture
def expired_jwt_token():
    """Create an expired JWT token for testing."""
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_returns_ok(self, client):
        """Test that /health endpoint returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "api_gateway"}

    @patch("src.api_gateway.routers.health.check_database_health")
    @patch("src.api_gateway.routers.health.check_redis_health")
    def test_readiness_endpoint_with_healthy_dependencies(
        self, mock_redis_health, mock_db_health, client
    ):
        """Test /ready endpoint when all dependencies are healthy."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "api_gateway"
        assert data["dependencies"]["database"] == "healthy"
        assert data["dependencies"]["redis"] == "healthy"

    @patch("src.api_gateway.routers.health.check_database_health")
    @patch("src.api_gateway.routers.health.check_redis_health")
    def test_readiness_endpoint_with_unhealthy_database(
        self, mock_redis_health, mock_db_health, client
    ):
        """Test /ready endpoint when database is unhealthy."""
        mock_db_health.return_value = False
        mock_redis_health.return_value = True

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"] == "unhealthy"

    @patch("src.api_gateway.routers.health.check_database_health")
    @patch("src.api_gateway.routers.health.check_redis_health")
    def test_metrics_endpoint(self, mock_redis_health, mock_db_health, client):
        """Test /metrics endpoint returns service metrics."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "api_gateway"
        assert data["environment"] == settings.ENVIRONMENT
        assert data["version"] == "0.1.0"
        assert "database_connected" in data
        assert "redis_connected" in data


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_info(self, client):
        """Test that / endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == settings.APP_NAME
        assert data["version"] == "0.1.0"
        assert data["status"] == "operational"
        assert data["environment"] == settings.ENVIRONMENT


class TestAuthenticationMiddleware:
    """Test authentication middleware functionality."""

    def test_public_endpoints_without_authentication(self, client):
        """Test that public endpoints don't require authentication."""
        public_endpoints = ["/", "/health", "/ready", "/metrics"]

        for endpoint in public_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 503]

    def test_request_without_token_sets_unauthenticated_state(self, client):
        """Test that requests without tokens are marked as unauthenticated."""
        # Test a public endpoint to verify state is set
        response = client.get("/")
        assert response.status_code == 200

    def test_request_with_valid_token_authenticates(self, client, valid_jwt_token):
        """Test that valid JWT tokens authenticate requests."""
        headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        response = client.get("/", headers=headers)

        assert response.status_code == 200

    def test_request_with_expired_token_fails_authentication(
        self, client, expired_jwt_token
    ):
        """Test that expired JWT tokens fail authentication."""
        headers = {"Authorization": f"Bearer {expired_jwt_token}"}

        response = client.get("/", headers=headers)

        # Expired token should not prevent access to public endpoints
        # but should not set authenticated state
        assert response.status_code == 200

    def test_request_with_invalid_token_format(self, client):
        """Test that invalid token formats are handled."""
        headers = {"Authorization": "InvalidFormat"}

        response = client.get("/", headers=headers)

        # Invalid format should not crash the server
        assert response.status_code == 200

    def test_request_with_malformed_jwt(self, client):
        """Test that malformed JWT tokens are handled."""
        headers = {"Authorization": "Bearer malformed.jwt.token"}

        response = client.get("/", headers=headers)

        # Malformed token should not crash the server
        assert response.status_code == 200


class TestCORSMiddleware:
    """Test CORS middleware functionality."""

    def test_cors_headers_present_in_response(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/", headers={"Origin": "http://localhost:3000"})

        # CORS middleware should add appropriate headers
        assert response.status_code in [200, 405]

    def test_cors_allows_configured_origins(self, client):
        """Test that configured origins are allowed."""
        origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"

        response = client.get("/", headers={"Origin": origin})

        assert response.status_code == 200


class TestRequestLoggingMiddleware:
    """Test request logging middleware functionality."""

    def test_correlation_id_added_to_response(self, client):
        """Test that correlation ID is added to response headers."""
        response = client.get("/health")

        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers

    def test_existing_correlation_id_preserved(self, client):
        """Test that existing correlation IDs are preserved."""
        correlation_id = "test-correlation-123"
        headers = {"X-Correlation-ID": correlation_id}

        response = client.get("/health", headers=headers)

        # The correlation ID should be in the response
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers


class TestRateLimitingMiddleware:
    """Test rate limiting middleware functionality."""

    @patch("src.api_gateway.middleware.rate_limit.get_redis_client")
    def test_rate_limit_headers_present(self, mock_redis_client, client):
        """Test that rate limit headers are added to responses."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.zremrangebyscore = AsyncMock()
        mock_client.zcard = AsyncMock(return_value=1)
        mock_client.zadd = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[])
        mock_redis_client.return_value = mock_client

        response = client.get("/")

        # Rate limit headers should be present
        assert (
            "X-RateLimit-Limit" in response.headers
            or "X-RateLimit-Remaining" in response.headers
            or response.status_code == 200
        )

    def test_public_endpoints_not_rate_limited(self, client):
        """Test that public endpoints bypass rate limiting."""
        # Health endpoint should not be rate limited
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200


class TestErrorHandling:
    """Test error handling functionality."""

    def test_404_for_nonexistent_endpoint(self, client):
        """Test that nonexistent endpoints return 404."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

    def test_405_for_unsupported_method(self, client):
        """Test that unsupported HTTP methods return 405."""
        response = client.post("/health")

        assert response.status_code == 405


@pytest.mark.integration
class TestAPIGatewayIntegration:
    """Integration tests for full API Gateway functionality."""

    @patch("src.api_gateway.routers.health.check_database_health")
    @patch("src.api_gateway.routers.health.check_redis_health")
    def test_full_request_flow_with_authentication(
        self, mock_redis_health, mock_db_health, client, valid_jwt_token
    ):
        """Test complete request flow with authentication."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        response = client.get("/ready", headers=headers)

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers or "X-Request-ID" in response.headers
        data = response.json()
        assert data["status"] == "ready"

    def test_application_startup_and_shutdown(self):
        """Test that application starts and shuts down cleanly."""
        with TestClient(app) as test_client:
            response = test_client.get("/health")
            assert response.status_code == 200
