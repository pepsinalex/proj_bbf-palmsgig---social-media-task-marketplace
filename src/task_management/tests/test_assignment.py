"""
Tests for Task Assignment Router.

Comprehensive tests for assignment API endpoints including assignment,
unassignment, eligibility checks, and retrieval operations.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)
from src.task_management.routers.assignment import router as assignment_router
from src.task_management.services.assignment_service import AssignmentService


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI application for testing."""
    app = FastAPI()
    app.include_router(assignment_router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_assignment_service() -> AssignmentService:
    """Create a mock assignment service."""
    service = AsyncMock(spec=AssignmentService)
    return service


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-123",
        creator_id="user-123",
        title="Test Task",
        description="Test Description",
        instructions="Test Instructions",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("1.00"),
        service_fee=Decimal("0.15"),
        total_cost=Decimal("1.15"),
        max_performers=10,
        current_performers=0,
        status=TaskStatusEnum.ACTIVE,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_assignment() -> TaskAssignment:
    """Create a sample assignment for testing."""
    return TaskAssignment(
        id="assignment-123",
        task_id="task-123",
        performer_id="user-456",
        status=AssignmentStatusEnum.ASSIGNED,
        assigned_at=datetime.utcnow(),
    )


class TestAssignTaskEndpoint:
    """Tests for POST /assignments endpoint."""

    def test_assign_task_success(
        self,
        client: TestClient,
        sample_task: Task,
        sample_assignment: TaskAssignment,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test successful task assignment."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        # Override dependencies
        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns task
            mock_session.get.return_value = sample_task

            # Mock assignment service returns assignment
            mock_assignment_service.assign_task.return_value = (
                sample_assignment,
                None,
            )

            response = client.post(
                "/assignments?performer_id=user-456",
                json={"task_id": "task-123"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == sample_assignment.id
            assert data["task_id"] == sample_assignment.task_id
            assert data["performer_id"] == sample_assignment.performer_id

    def test_assign_task_not_found(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test assignment when task not found."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns None
            mock_session.get.return_value = None

            response = client.post(
                "/assignments?performer_id=user-456",
                json={"task_id": "task-123"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_assign_task_validation_failure(
        self,
        client: TestClient,
        sample_task: Task,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test assignment when validation fails."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns task
            mock_session.get.return_value = sample_task

            # Mock assignment service returns error
            mock_assignment_service.assign_task.return_value = (
                None,
                "Not eligible to accept this task",
            )

            response = client.post(
                "/assignments?performer_id=user-456",
                json={"task_id": "task-123"},
            )

            assert response.status_code == 400
            assert "not eligible" in response.json()["detail"].lower()


class TestUnassignTaskEndpoint:
    """Tests for DELETE /assignments/{assignment_id} endpoint."""

    def test_unassign_task_success(
        self,
        client: TestClient,
        sample_assignment: TaskAssignment,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test successful task unassignment."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns assignment
            mock_session.get.return_value = sample_assignment

            # Mock unassign succeeds
            mock_assignment_service.unassign_task.return_value = (True, None)

            response = client.delete("/assignments/assignment-123")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_unassign_task_not_found(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test unassignment when assignment not found."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns None
            mock_session.get.return_value = None

            response = client.delete("/assignments/assignment-123")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_unassign_task_failure(
        self,
        client: TestClient,
        sample_assignment: TaskAssignment,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test unassignment when operation fails."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns assignment
            mock_session.get.return_value = sample_assignment

            # Mock unassign fails
            mock_assignment_service.unassign_task.return_value = (
                False,
                "Cannot unassign completed task",
            )

            response = client.delete("/assignments/assignment-123")

            assert response.status_code == 400


class TestGetUserAssignmentsEndpoint:
    """Tests for GET /assignments/user/{user_id} endpoint."""

    def test_get_user_assignments_success(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test retrieving user assignments."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        # Create sample assignments
        assignments = [
            TaskAssignment(
                id=f"assignment-{i}",
                task_id=f"task-{i}",
                performer_id="user-456",
                status=AssignmentStatusEnum.ASSIGNED,
                assigned_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock service returns assignments
            mock_assignment_service.get_user_assignments.return_value = assignments

            response = client.get("/assignments/user/user-456")

            assert response.status_code == 200
            data = response.json()
            assert len(data["assignments"]) == 3
            assert data["total"] == 3

    def test_get_user_assignments_with_filter(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test retrieving user assignments with status filter."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        assignments = [
            TaskAssignment(
                id="assignment-1",
                task_id="task-1",
                performer_id="user-456",
                status=AssignmentStatusEnum.STARTED,
                assigned_at=datetime.utcnow(),
            )
        ]

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            mock_assignment_service.get_user_assignments.return_value = assignments

            response = client.get("/assignments/user/user-456?status=STARTED")

            assert response.status_code == 200
            data = response.json()
            assert len(data["assignments"]) == 1

    def test_get_user_assignments_with_pagination(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test retrieving user assignments with pagination."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        assignments = [
            TaskAssignment(
                id=f"assignment-{i}",
                task_id=f"task-{i}",
                performer_id="user-456",
                status=AssignmentStatusEnum.ASSIGNED,
                assigned_at=datetime.utcnow(),
            )
            for i in range(10)
        ]

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            mock_assignment_service.get_user_assignments.return_value = assignments

            response = client.get("/assignments/user/user-456?limit=10&offset=5")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5

    def test_get_user_assignments_empty(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test retrieving user assignments when none exist."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            mock_assignment_service.get_user_assignments.return_value = []

            response = client.get("/assignments/user/user-456")

            assert response.status_code == 200
            data = response.json()
            assert len(data["assignments"]) == 0
            assert data["total"] == 0


class TestGetAssignmentEndpoint:
    """Tests for GET /assignments/{assignment_id} endpoint."""

    def test_get_assignment_success(
        self,
        client: TestClient,
        sample_assignment: TaskAssignment,
        mock_session: AsyncSession,
    ) -> None:
        """Test retrieving assignment details."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ):
            # Mock session.get returns assignment
            mock_session.get.return_value = sample_assignment

            response = client.get("/assignments/assignment-123")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_assignment.id
            assert data["task_id"] == sample_assignment.task_id
            assert data["performer_id"] == sample_assignment.performer_id

    def test_get_assignment_not_found(
        self, client: TestClient, mock_session: AsyncSession
    ) -> None:
        """Test retrieving assignment when not found."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ):
            # Mock session.get returns None
            mock_session.get.return_value = None

            response = client.get("/assignments/assignment-123")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestCheckEligibilityEndpoint:
    """Tests for GET /assignments/eligibility/check endpoint."""

    def test_check_eligibility_eligible(
        self,
        client: TestClient,
        sample_task: Task,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test eligibility check when performer is eligible."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns task
            mock_session.get.return_value = sample_task

            # Mock eligibility check passes
            mock_assignment_service.validate_performer_eligibility.return_value = (
                True,
                None,
            )
            mock_assignment_service.check_concurrent_limits.return_value = (2, 5)

            response = client.get(
                "/assignments/eligibility/check?performer_id=user-456&task_id=task-123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["eligible"] is True
            assert data["concurrent_tasks"] == 2
            assert data["max_concurrent"] == 5

    def test_check_eligibility_not_eligible(
        self,
        client: TestClient,
        sample_task: Task,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test eligibility check when performer is not eligible."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns task
            mock_session.get.return_value = sample_task

            # Mock eligibility check fails
            mock_assignment_service.validate_performer_eligibility.return_value = (
                False,
                "Maximum concurrent tasks reached",
            )
            mock_assignment_service.check_concurrent_limits.return_value = (5, 5)

            response = client.get(
                "/assignments/eligibility/check?performer_id=user-456&task_id=task-123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["eligible"] is False
            assert "maximum concurrent" in data["reason"].lower()

    def test_check_eligibility_task_not_found(
        self,
        client: TestClient,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test eligibility check when task not found."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # Mock session.get returns None
            mock_session.get.return_value = None

            response = client.get(
                "/assignments/eligibility/check?performer_id=user-456&task_id=task-123"
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestAssignmentRouterIntegration:
    """Integration tests for assignment router."""

    def test_full_assignment_lifecycle(
        self,
        client: TestClient,
        sample_task: Task,
        sample_assignment: TaskAssignment,
        mock_session: AsyncSession,
        mock_assignment_service: AssignmentService,
    ) -> None:
        """Test complete assignment lifecycle."""

        async def mock_get_db_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        async def mock_get_assignment_service() -> AssignmentService:
            return mock_assignment_service

        with patch(
            "src.task_management.routers.assignment.get_db_session",
            mock_get_db_session,
        ), patch(
            "src.task_management.routers.assignment.get_assignment_service",
            mock_get_assignment_service,
        ):
            # 1. Check eligibility
            mock_session.get.return_value = sample_task
            mock_assignment_service.validate_performer_eligibility.return_value = (
                True,
                None,
            )
            mock_assignment_service.check_concurrent_limits.return_value = (2, 5)

            eligibility_response = client.get(
                "/assignments/eligibility/check?performer_id=user-456&task_id=task-123"
            )
            assert eligibility_response.status_code == 200
            assert eligibility_response.json()["eligible"] is True

            # 2. Assign task
            mock_session.get.return_value = sample_task
            mock_assignment_service.assign_task.return_value = (
                sample_assignment,
                None,
            )

            assign_response = client.post(
                "/assignments?performer_id=user-456",
                json={"task_id": "task-123"},
            )
            assert assign_response.status_code == 201

            # 3. Get assignment details
            mock_session.get.return_value = sample_assignment

            get_response = client.get("/assignments/assignment-123")
            assert get_response.status_code == 200

            # 4. Unassign task
            mock_session.get.return_value = sample_assignment
            mock_assignment_service.unassign_task.return_value = (True, None)

            unassign_response = client.delete("/assignments/assignment-123")
            assert unassign_response.status_code == 200
            assert unassign_response.json()["success"] is True
