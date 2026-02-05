"""
Tests for Task Management API Routers.

Comprehensive tests for task API endpoints including
authentication, authorization, validation, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.task_management.main import app
from src.task_management.models.task import (
    PlatformEnum,
    Task,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.services.task_service import TaskService


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_service() -> AsyncMock:
    """Create mock TaskService."""
    return AsyncMock(spec=TaskService)


@pytest.fixture
def sample_task() -> Task:
    """Create sample task."""
    return Task(
        id="task-123",
        creator_id="user-123",
        title="Like my Instagram post",
        description="Need 100 likes on my latest post",
        instructions="1. Visit post\n2. Click like\n3. Screenshot",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("10.00"),
        service_fee=Decimal("1.50"),
        total_cost=Decimal("11.50"),
        max_performers=100,
        current_performers=0,
        status=TaskStatusEnum.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestCreateTaskEndpoint:
    """Tests for POST /tasks endpoint."""

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_create_task_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_task: Task,
    ) -> None:
        """Test successful task creation."""
        # Setup mocks
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_task.return_value = sample_task
        mock_get_service.return_value = mock_service

        # Create request
        task_data = {
            "title": "Like my Instagram post",
            "description": "Need 100 likes on my latest post",
            "instructions": "1. Visit post\n2. Click like\n3. Screenshot",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post("/api/v1/tasks", json=task_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "task-123"
        assert data["title"] == "Like my Instagram post"
        assert data["status"] == "active"
        assert data["service_fee"] == "1.50"
        assert data["total_cost"] == "11.50"

    @patch("src.task_management.routers.tasks.get_current_user_id")
    async def test_create_task_validation_error(
        self, mock_get_user: MagicMock, client: TestClient
    ) -> None:
        """Test task creation with invalid data."""
        mock_get_user.return_value = "user-123"

        # Missing required fields
        task_data = {
            "title": "Test",
        }

        response = client.post("/api/v1/tasks", json=task_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_create_task_service_error(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test task creation with service error."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_task.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service

        task_data = {
            "title": "Like my Instagram post",
            "description": "Need 100 likes on my latest post",
            "instructions": "1. Visit post\n2. Click like\n3. Screenshot",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post("/api/v1/tasks", json=task_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestListTasksEndpoint:
    """Tests for GET /tasks endpoint."""

    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_list_tasks_success(
        self, mock_get_service: MagicMock, client: TestClient, sample_task: Task
    ) -> None:
        """Test successful task listing."""
        mock_service = AsyncMock()
        mock_service.list_tasks.return_value = ([sample_task], 1)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == "task-123"

    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_list_tasks_with_pagination(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test task listing with pagination."""
        mock_service = AsyncMock()
        mock_service.list_tasks.return_value = ([], 50)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks?page=2&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total"] == 50
        assert data["total_pages"] == 5

    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_list_tasks_with_filters(
        self, mock_get_service: MagicMock, client: TestClient, sample_task: Task
    ) -> None:
        """Test task listing with filters."""
        mock_service = AsyncMock()
        mock_service.list_tasks.return_value = ([sample_task], 1)
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/tasks?status=active&platform=instagram&search=like"
        )

        assert response.status_code == status.HTTP_200_OK
        mock_service.list_tasks.assert_called_once()


class TestGetTaskEndpoint:
    """Tests for GET /tasks/{task_id} endpoint."""

    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_get_task_success(
        self, mock_get_service: MagicMock, client: TestClient, sample_task: Task
    ) -> None:
        """Test successful task retrieval."""
        mock_service = AsyncMock()
        mock_service.get_task.return_value = sample_task
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks/task-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "task-123"
        assert data["title"] == "Like my Instagram post"

    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_get_task_not_found(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test getting non-existent task."""
        mock_service = AsyncMock()
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


class TestUpdateTaskEndpoint:
    """Tests for PUT /tasks/{task_id} endpoint."""

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_update_task_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_task: Task,
    ) -> None:
        """Test successful task update."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = sample_task

        updated_task = sample_task
        updated_task.title = "Updated Title"
        mock_service.update_task.return_value = updated_task
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put("/api/v1/tasks/task-123", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_update_task_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test updating non-existent task."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put("/api/v1/tasks/nonexistent", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_update_task_unauthorized(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_task: Task,
    ) -> None:
        """Test updating task by non-creator."""
        mock_get_user.return_value = "other-user"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = sample_task
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put("/api/v1/tasks/task-123", json=update_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only update your own" in response.json()["detail"].lower()


class TestDeleteTaskEndpoint:
    """Tests for DELETE /tasks/{task_id} endpoint."""

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_delete_task_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_task: Task,
    ) -> None:
        """Test successful task deletion."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = sample_task
        mock_service.delete_task.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/task-123")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_delete_task_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test deleting non-existent task."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.task_management.routers.tasks.get_current_user_id")
    @patch("src.task_management.routers.tasks.get_task_service")
    async def test_delete_task_unauthorized(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_task: Task,
    ) -> None:
        """Test deleting task by non-creator."""
        mock_get_user.return_value = "other-user"
        mock_service = AsyncMock()
        mock_service.get_task.return_value = sample_task
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/task-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only delete your own" in response.json()["detail"].lower()


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "task_management"

    @patch("src.task_management.main.check_database_health")
    @patch("src.task_management.main.check_redis_health")
    async def test_readiness_check_healthy(
        self,
        mock_redis_health: MagicMock,
        mock_db_health: MagicMock,
        client: TestClient,
    ) -> None:
        """Test readiness check with healthy dependencies."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        response = client.get("/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "healthy"
        assert data["redis"] == "healthy"

    @patch("src.task_management.main.check_database_health")
    @patch("src.task_management.main.check_redis_health")
    async def test_readiness_check_unhealthy(
        self,
        mock_redis_health: MagicMock,
        mock_db_health: MagicMock,
        client: TestClient,
    ) -> None:
        """Test readiness check with unhealthy dependencies."""
        mock_db_health.return_value = False
        mock_redis_health.return_value = True

        response = client.get("/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "not ready"
        assert data["database"] == "unhealthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["service"] == "Task Management Service"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
