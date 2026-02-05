"""
Tests for Task Creation and Draft Management API Endpoints.

Comprehensive tests for draft creation, publishing, updating,
and deletion with authentication, validation, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.task_management.enums.task_enums import (
    PlatformEnum,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.main import app
from src.task_management.models.task import Task
from src.task_management.services.task_service import TaskService
from src.task_management.services.validation_service import ValidationError


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_service() -> AsyncMock:
    """Create mock TaskService."""
    return AsyncMock(spec=TaskService)


@pytest.fixture
def sample_draft() -> Task:
    """Create sample draft task."""
    return Task(
        id="draft-123",
        creator_id="user-123",
        title="My Draft Task",
        description="",
        instructions="",
        platform=None,
        task_type=None,
        budget=Decimal("0.00"),
        service_fee=Decimal("0.00"),
        total_cost=Decimal("0.00"),
        max_performers=0,
        current_performers=0,
        status=TaskStatusEnum.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_complete_draft() -> Task:
    """Create sample complete draft task."""
    return Task(
        id="draft-456",
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
        status=TaskStatusEnum.DRAFT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_published_task() -> Task:
    """Create sample published task."""
    return Task(
        id="task-789",
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
        status=TaskStatusEnum.PENDING_PAYMENT,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestCreateDraftEndpoint:
    """Tests for POST /tasks/draft endpoint."""

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_create_draft_minimal_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test creating a minimal draft with only title."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_draft.return_value = sample_draft
        mock_get_service.return_value = mock_service

        draft_data = {"title": "My Draft Task"}

        response = client.post("/api/v1/tasks/draft", json=draft_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "draft-123"
        assert data["title"] == "My Draft Task"
        assert data["status"] == "draft"
        assert data["creator_id"] == "user-123"

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_create_draft_complete_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_complete_draft: Task,
    ) -> None:
        """Test creating a complete draft with all fields."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_draft.return_value = sample_complete_draft
        mock_get_service.return_value = mock_service

        draft_data = {
            "title": "Like my Instagram post",
            "description": "Need 100 likes on my latest post",
            "instructions": "1. Visit post\n2. Click like\n3. Screenshot",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post("/api/v1/tasks/draft", json=draft_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "draft-456"
        assert data["title"] == "Like my Instagram post"
        assert data["platform"] == "instagram"
        assert data["budget"] == "10.00"
        assert data["fee_breakdown"] is not None

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_create_draft_validation_error(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test draft creation with validation error."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_draft.side_effect = ValidationError("Title is required")
        mock_get_service.return_value = mock_service

        draft_data = {"title": ""}

        response = client.post("/api/v1/tasks/draft", json=draft_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Title is required" in response.json()["detail"]


class TestPublishTaskEndpoint:
    """Tests for POST /tasks/{task_id}/publish endpoint."""

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_publish_task_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_complete_draft: Task,
        sample_published_task: Task,
    ) -> None:
        """Test successfully publishing a draft task."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = sample_complete_draft
        mock_service.publish_task.return_value = sample_published_task
        mock_get_service.return_value = mock_service

        publish_data = {
            "title": "Like my Instagram post",
            "description": "Need 100 likes on my latest post",
            "instructions": "1. Visit post\n2. Click like\n3. Screenshot",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post(
            "/api/v1/tasks/draft-456/publish", json=publish_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "task-789"
        assert data["status"] == "pending_payment"
        assert data["fee_breakdown"] is not None

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_publish_task_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test publishing a non-existent task."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        publish_data = {
            "title": "Like my post",
            "description": "Need likes",
            "instructions": "Click like",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post(
            "/api/v1/tasks/nonexistent/publish", json=publish_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_publish_task_unauthorized(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_complete_draft: Task,
    ) -> None:
        """Test publishing another user's task."""
        mock_get_user.return_value = "user-456"
        sample_complete_draft.creator_id = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = sample_complete_draft
        mock_get_service.return_value = mock_service

        publish_data = {
            "title": "Like my post",
            "description": "Need likes",
            "instructions": "Click like",
            "platform": "instagram",
            "task_type": "like",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post(
            "/api/v1/tasks/draft-456/publish", json=publish_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_publish_task_validation_error(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_complete_draft: Task,
    ) -> None:
        """Test publishing with validation errors."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = sample_complete_draft
        mock_service.publish_task.side_effect = ValidationError(
            "Platform-task type incompatible"
        )
        mock_get_service.return_value = mock_service

        publish_data = {
            "title": "Subscribe",
            "description": "Subscribe to me",
            "instructions": "Click subscribe",
            "platform": "facebook",
            "task_type": "subscribe",
            "budget": 10.00,
            "max_performers": 100,
        }

        response = client.post(
            "/api/v1/tasks/draft-456/publish", json=publish_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestListDraftsEndpoint:
    """Tests for GET /tasks/drafts endpoint."""

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_list_drafts_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
        sample_complete_draft: Task,
    ) -> None:
        """Test listing user's drafts."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.list_drafts.return_value = (
            [sample_draft, sample_complete_draft],
            2,
        )
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks/drafts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "draft-123"
        assert data[1]["id"] == "draft-456"

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_list_drafts_empty(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test listing drafts when user has none."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.list_drafts.return_value = ([], 0)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks/drafts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_list_drafts_with_pagination(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test listing drafts with pagination parameters."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.list_drafts.return_value = ([sample_draft], 5)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/tasks/drafts?skip=2&limit=1")

        assert response.status_code == status.HTTP_200_OK
        mock_service.list_drafts.assert_called_once()


class TestUpdateDraftEndpoint:
    """Tests for PUT /tasks/drafts/{draft_id} endpoint."""

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_update_draft_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test successfully updating a draft."""
        mock_get_user.return_value = "user-123"
        updated_draft = sample_draft
        updated_draft.title = "Updated Title"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = sample_draft
        mock_service.update_draft.return_value = updated_draft
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put(
            "/api/v1/tasks/drafts/draft-123", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_update_draft_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test updating a non-existent draft."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put(
            "/api/v1/tasks/drafts/nonexistent", json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_update_draft_unauthorized(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test updating another user's draft."""
        mock_get_user.return_value = "user-456"
        sample_draft.creator_id = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = sample_draft
        mock_get_service.return_value = mock_service

        update_data = {"title": "Updated Title"}

        response = client.put(
            "/api/v1/tasks/drafts/draft-123", json=update_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteDraftEndpoint:
    """Tests for DELETE /tasks/drafts/{draft_id} endpoint."""

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_delete_draft_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test successfully deleting a draft."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = sample_draft
        mock_service.delete_task.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/drafts/draft-123")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_delete_draft_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test deleting a non-existent draft."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = None
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/drafts/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_delete_draft_unauthorized(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_draft: Task,
    ) -> None:
        """Test deleting another user's draft."""
        mock_get_user.return_value = "user-456"
        sample_draft.creator_id = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = sample_draft
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/drafts/draft-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.task_management.routers.task_creation.get_current_user_id")
    @patch("src.task_management.routers.task_creation.get_task_service")
    def test_delete_non_draft_task(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_published_task: Task,
    ) -> None:
        """Test deleting a non-draft task via draft endpoint."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_draft.return_value = None
        mock_service.get_task.return_value = sample_published_task
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/tasks/drafts/task-789")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not a draft" in response.json()["detail"]
