"""
Tests for Task Discovery API Router.

Comprehensive tests for discovery API endpoints including available tasks,
search, recommendations, and task details retrieval.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.task_management.main import app
from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.schemas.discovery import (
    RecommendationResponse,
    TaskDiscoveryResponse,
)
from src.task_management.services.discovery_service import DiscoveryService
from src.task_management.services.recommendation_service import RecommendationService


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_discovery_service() -> AsyncMock:
    """Create mock DiscoveryService."""
    return AsyncMock(spec=DiscoveryService)


@pytest.fixture
def mock_recommendation_service() -> AsyncMock:
    """Create mock RecommendationService."""
    return AsyncMock(spec=RecommendationService)


@pytest.fixture
def sample_task_response() -> TaskDiscoveryResponse:
    """Create sample task discovery response."""
    return TaskDiscoveryResponse(
        id="task-123",
        title="Like my Instagram post",
        description="Need 100 likes on my latest post about travel",
        instructions="1. Visit the post URL\n2. Click like\n3. Screenshot proof",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("10.00"),
        service_fee=Decimal("1.50"),
        total_cost=Decimal("11.50"),
        max_performers=100,
        current_performers=25,
        status=TaskStatusEnum.ACTIVE,
        creator_id="creator-456",
        target_criteria={"countries": ["US", "CA"], "min_age": 18},
        expires_at=datetime.utcnow() + timedelta(days=7),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_task_responses() -> list[TaskDiscoveryResponse]:
    """Create multiple sample task discovery responses."""
    now = datetime.utcnow()
    return [
        TaskDiscoveryResponse(
            id=f"task-{i}",
            title=f"Task {i}",
            description=f"Description {i}",
            instructions=f"Instructions {i}",
            platform=PlatformEnum.INSTAGRAM if i % 2 == 0 else PlatformEnum.FACEBOOK,
            task_type=TaskTypeEnum.LIKE if i % 2 == 0 else TaskTypeEnum.FOLLOW,
            budget=Decimal(f"{i + 5}.00"),
            service_fee=Decimal(f"{(i + 5) * 0.15:.2f}"),
            total_cost=Decimal(f"{(i + 5) * 1.15:.2f}"),
            max_performers=100,
            current_performers=i * 10,
            status=TaskStatusEnum.ACTIVE,
            creator_id=f"creator-{i}",
            target_criteria={},
            expires_at=now + timedelta(days=7),
            created_at=now - timedelta(hours=i),
            updated_at=now,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_recommendation() -> RecommendationResponse:
    """Create sample recommendation response."""
    task_response = TaskDiscoveryResponse(
        id="task-999",
        title="Recommended Instagram task",
        description="Task matching your preferences",
        instructions="Follow instructions carefully",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("8.00"),
        service_fee=Decimal("1.20"),
        total_cost=Decimal("9.20"),
        max_performers=50,
        current_performers=10,
        status=TaskStatusEnum.ACTIVE,
        creator_id="creator-999",
        target_criteria={},
        expires_at=datetime.utcnow() + timedelta(days=5),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    return RecommendationResponse(
        task=task_response,
        match_score=0.85,
        recommendation_reason="Strong match for your Instagram experience",
        factors={
            "platform_affinity": 0.9,
            "task_type_preference": 0.8,
            "budget_compatibility": 0.85,
            "availability": 0.9,
            "freshness": 0.95,
        },
    )


class TestGetAvailableTasksEndpoint:
    """Tests for GET /discovery/available endpoint."""

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_success(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test successful retrieval of available tasks."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.return_value = (
            sample_task_responses,
            5,
        )

        response = client.get("/api/v1/discovery/available")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tasks" in data
        assert "pagination" in data
        assert len(data["tasks"]) == 5
        assert data["pagination"]["total_count"] == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_with_pagination(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test available tasks with pagination parameters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.return_value = (
            sample_task_responses[:2],
            5,
        )

        response = client.get("/api/v1/discovery/available?page=2&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_count"] == 5
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_previous"] is True

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_with_filters(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test available tasks with filter parameters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.return_value = (
            sample_task_responses[:3],
            3,
        )

        response = client.get(
            "/api/v1/discovery/available"
            "?platform=instagram"
            "&task_type=like"
            "&min_budget=5.0"
            "&max_budget=15.0"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filters_applied" in data
        assert len(data["tasks"]) == 3

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_with_sorting(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test available tasks with sorting parameters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.return_value = (
            sample_task_responses,
            5,
        )

        response = client.get(
            "/api/v1/discovery/available?sort_by=budget&sort_order=asc"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filters_applied"]["sort_by"] == "budget"
        assert data["filters_applied"]["sort_order"] == "asc"

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_empty_result(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test available tasks with no matching results."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.return_value = ([], 0)

        response = client.get("/api/v1/discovery/available")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["tasks"]) == 0
        assert data["pagination"]["total_count"] == 0
        assert data["pagination"]["total_pages"] == 0

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_invalid_parameters(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test available tasks with invalid parameters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.side_effect = ValueError(
            "Invalid sort_by field"
        )

        response = client.get("/api/v1/discovery/available?sort_by=invalid_field")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid filter parameters" in response.json()["detail"]

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_available_tasks_server_error(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test available tasks handles server errors."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_available_tasks.side_effect = Exception(
            "Database error"
        )

        response = client.get("/api/v1/discovery/available")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve available tasks" in response.json()["detail"]


class TestSearchTasksEndpoint:
    """Tests for GET /discovery/search endpoint."""

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_success(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test successful task search."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.return_value = (
            sample_task_responses[:3],
            3,
        )

        response = client.get("/api/v1/discovery/search?q=Instagram")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tasks" in data
        assert "pagination" in data
        assert "search_params" in data
        assert data["search_params"]["query"] == "Instagram"
        assert len(data["tasks"]) == 3
        assert data["pagination"]["total_count"] == 3

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_with_search_fields(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test search with specific search fields."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.return_value = (
            sample_task_responses[:2],
            2,
        )

        response = client.get(
            "/api/v1/discovery/search?q=like&search_fields=title&search_fields=description"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["search_params"]["search_fields"] == ["title", "description"]

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_with_filters(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test search with additional filters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.return_value = (
            sample_task_responses[:1],
            1,
        )

        response = client.get(
            "/api/v1/discovery/search"
            "?q=Instagram"
            "&platform=instagram"
            "&min_budget=5.0"
            "&max_budget=15.0"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "filters_applied" in data
        assert len(data["tasks"]) == 1

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_with_pagination(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_responses: list[TaskDiscoveryResponse],
    ) -> None:
        """Test search with pagination."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.return_value = (
            sample_task_responses[2:4],
            5,
        )

        response = client.get(
            "/api/v1/discovery/search?q=task&page=2&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_count"] == 5

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_empty_result(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test search with no matching results."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.return_value = ([], 0)

        response = client.get("/api/v1/discovery/search?q=nonexistent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["tasks"]) == 0
        assert data["pagination"]["total_count"] == 0

    def test_search_tasks_missing_query(self, client: TestClient) -> None:
        """Test search without query parameter."""
        response = client.get("/api/v1/discovery/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_invalid_parameters(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test search with invalid parameters."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.side_effect = ValueError(
            "Invalid search fields"
        )

        response = client.get("/api/v1/discovery/search?q=test")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid search parameters" in response.json()["detail"]

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_search_tasks_server_error(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test search handles server errors."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.search_tasks.side_effect = Exception("Search failed")

        response = client.get("/api/v1/discovery/search?q=test")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Search operation failed" in response.json()["detail"]


class TestGetRecommendedTasksEndpoint:
    """Tests for GET /discovery/recommended endpoint."""

    @patch("src.task_management.routers.discovery.get_current_user_id")
    @patch("src.task_management.routers.discovery.get_recommendation_service")
    def test_get_recommended_tasks_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        mock_recommendation_service: AsyncMock,
        sample_recommendation: RecommendationResponse,
    ) -> None:
        """Test successful recommendation retrieval."""
        mock_get_user.return_value = "user-123"
        mock_get_service.return_value = mock_recommendation_service
        mock_recommendation_service.generate_recommendations.return_value = [
            sample_recommendation
        ]

        response = client.get("/api/v1/discovery/recommended")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "recommendations" in data
        assert "total_count" in data
        assert "user_id" in data
        assert data["user_id"] == "user-123"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["match_score"] == 0.85

    @patch("src.task_management.routers.discovery.get_current_user_id")
    @patch("src.task_management.routers.discovery.get_recommendation_service")
    def test_get_recommended_tasks_with_limit(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        mock_recommendation_service: AsyncMock,
        sample_recommendation: RecommendationResponse,
    ) -> None:
        """Test recommendations with custom limit."""
        mock_get_user.return_value = "user-123"
        mock_get_service.return_value = mock_recommendation_service
        recommendations = [sample_recommendation] * 5
        mock_recommendation_service.generate_recommendations.return_value = (
            recommendations
        )

        response = client.get("/api/v1/discovery/recommended?limit=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["parameters"]["limit"] == 5
        assert len(data["recommendations"]) == 5

    @patch("src.task_management.routers.discovery.get_current_user_id")
    @patch("src.task_management.routers.discovery.get_recommendation_service")
    def test_get_recommended_tasks_with_min_score(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        mock_recommendation_service: AsyncMock,
        sample_recommendation: RecommendationResponse,
    ) -> None:
        """Test recommendations with minimum score threshold."""
        mock_get_user.return_value = "user-123"
        mock_get_service.return_value = mock_recommendation_service
        mock_recommendation_service.generate_recommendations.return_value = [
            sample_recommendation
        ]

        response = client.get("/api/v1/discovery/recommended?min_score=0.7")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["parameters"]["min_score"] == 0.7
        assert all(
            rec["match_score"] >= 0.7 for rec in data["recommendations"]
        )

    @patch("src.task_management.routers.discovery.get_current_user_id")
    @patch("src.task_management.routers.discovery.get_recommendation_service")
    def test_get_recommended_tasks_empty_result(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        mock_recommendation_service: AsyncMock,
    ) -> None:
        """Test recommendations with no results."""
        mock_get_user.return_value = "user-123"
        mock_get_service.return_value = mock_recommendation_service
        mock_recommendation_service.generate_recommendations.return_value = []

        response = client.get("/api/v1/discovery/recommended")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["recommendations"]) == 0
        assert data["total_count"] == 0

    @patch("src.task_management.routers.discovery.get_current_user_id")
    @patch("src.task_management.routers.discovery.get_recommendation_service")
    def test_get_recommended_tasks_server_error(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        mock_recommendation_service: AsyncMock,
    ) -> None:
        """Test recommendations handle server errors."""
        mock_get_user.return_value = "user-123"
        mock_get_service.return_value = mock_recommendation_service
        mock_recommendation_service.generate_recommendations.side_effect = Exception(
            "Recommendation failed"
        )

        response = client.get("/api/v1/discovery/recommended")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to generate recommendations" in response.json()["detail"]


class TestGetTaskDetailsEndpoint:
    """Tests for GET /discovery/tasks/{task_id} endpoint."""

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_task_details_success(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
        sample_task_response: TaskDiscoveryResponse,
    ) -> None:
        """Test successful task details retrieval."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_task_by_id.return_value = sample_task_response

        response = client.get("/api/v1/discovery/tasks/task-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "task-123"
        assert data["title"] == "Like my Instagram post"
        assert data["platform"] == "instagram"
        assert data["task_type"] == "like"

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_task_details_not_found(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test task details for non-existent task."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_task_by_id.return_value = None

        response = client.get("/api/v1/discovery/tasks/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @patch("src.task_management.routers.discovery.get_discovery_service")
    def test_get_task_details_server_error(
        self,
        mock_get_service: MagicMock,
        client: TestClient,
        mock_discovery_service: AsyncMock,
    ) -> None:
        """Test task details handles server errors."""
        mock_get_service.return_value = mock_discovery_service
        mock_discovery_service.get_task_by_id.side_effect = Exception("Database error")

        response = client.get("/api/v1/discovery/tasks/task-123")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve task details" in response.json()["detail"]


class TestDiscoveryDependencies:
    """Tests for discovery router dependencies."""

    @patch("src.task_management.routers.discovery.get_database_session")
    def test_get_discovery_service_dependency(
        self, mock_get_session: MagicMock
    ) -> None:
        """Test get_discovery_service dependency."""
        from src.task_management.routers.discovery import get_discovery_service

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        service = get_discovery_service(mock_session)

        assert isinstance(service, DiscoveryService)
        assert service.db_session == mock_session

    @patch("src.task_management.routers.discovery.get_database_session")
    def test_get_recommendation_service_dependency(
        self, mock_get_session: MagicMock
    ) -> None:
        """Test get_recommendation_service dependency."""
        from src.task_management.routers.discovery import get_recommendation_service

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        service = get_recommendation_service(mock_session)

        assert isinstance(service, RecommendationService)
        assert service.db_session == mock_session
