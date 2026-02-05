"""
Tests for Task Service.

Comprehensive tests for TaskService including CRUD operations,
service fee calculations, and business logic.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.models.task import (
    PlatformEnum,
    Task,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.schemas.task import TaskCreate, TaskUpdate
from src.task_management.services.task_service import TaskService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def task_service(mock_session: AsyncMock) -> TaskService:
    """Create TaskService instance with mock session."""
    return TaskService(mock_session)


@pytest.fixture
def sample_task_data() -> TaskCreate:
    """Create sample task creation data."""
    return TaskCreate(
        title="Like my Instagram post",
        description="Need 100 likes on my latest post about travel",
        instructions="1. Visit the post URL\n2. Click like\n3. Screenshot proof",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("10.00"),
        max_performers=100,
        target_criteria={"countries": ["US", "CA"], "min_age": 18},
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


class TestTaskServiceCreate:
    """Tests for task creation."""

    async def test_create_task_success(
        self, task_service: TaskService, mock_session: AsyncMock, sample_task_data: TaskCreate
    ) -> None:
        """Test successful task creation."""
        creator_id = "user-123"

        task = await task_service.create_task(creator_id, sample_task_data)

        assert task.creator_id == creator_id
        assert task.title == sample_task_data.title
        assert task.platform == sample_task_data.platform
        assert task.task_type == sample_task_data.task_type
        assert task.budget == sample_task_data.budget
        assert task.status == TaskStatusEnum.DRAFT
        assert task.current_performers == 0

        # Verify service fee calculation (15% of budget)
        expected_fee = Decimal("1.50")
        expected_total = Decimal("11.50")
        assert task.service_fee == expected_fee
        assert task.total_cost == expected_total

        # Verify session interactions
        assert mock_session.add.call_count == 2  # Task + History
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_task_calculates_service_fee(
        self, task_service: TaskService, mock_session: AsyncMock, sample_task_data: TaskCreate
    ) -> None:
        """Test service fee calculation."""
        sample_task_data.budget = Decimal("20.00")

        task = await task_service.create_task("user-123", sample_task_data)

        # 15% of 20.00 = 3.00
        assert task.service_fee == Decimal("3.00")
        assert task.total_cost == Decimal("23.00")

    async def test_create_task_with_minimal_budget(
        self, task_service: TaskService, mock_session: AsyncMock, sample_task_data: TaskCreate
    ) -> None:
        """Test service fee with minimal budget."""
        sample_task_data.budget = Decimal("0.50")

        task = await task_service.create_task("user-123", sample_task_data)

        # 15% of 0.50 = 0.075, rounded to 0.08
        assert task.service_fee == Decimal("0.08")
        assert task.total_cost == Decimal("0.58")


class TestTaskServiceRead:
    """Tests for reading tasks."""

    async def test_get_task_found(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test getting an existing task."""
        task_id = "task-123"
        mock_task = Task(
            id=task_id,
            creator_id="user-123",
            title="Test Task",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            status=TaskStatusEnum.ACTIVE,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_session.execute.return_value = mock_result

        task = await task_service.get_task(task_id)

        assert task is not None
        assert task.id == task_id
        assert task.title == "Test Task"
        mock_session.execute.assert_called_once()

    async def test_get_task_not_found(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test getting a non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        task = await task_service.get_task("nonexistent-123")

        assert task is None


class TestTaskServiceUpdate:
    """Tests for updating tasks."""

    async def test_update_task_success(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test successful task update."""
        task_id = "task-123"
        user_id = "user-123"

        existing_task = Task(
            id=task_id,
            creator_id=user_id,
            title="Original Title",
            description="Original description",
            instructions="Original instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            status=TaskStatusEnum.DRAFT,
        )

        # Mock get_task to return existing task
        task_service.get_task = AsyncMock(return_value=existing_task)

        update_data = TaskUpdate(title="Updated Title", status=TaskStatusEnum.ACTIVE)

        task = await task_service.update_task(task_id, user_id, update_data)

        assert task is not None
        assert task.title == "Updated Title"
        assert task.status == TaskStatusEnum.ACTIVE
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_update_task_recalculates_fees_on_budget_change(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test fee recalculation when budget is updated."""
        task_id = "task-123"
        user_id = "user-123"

        existing_task = Task(
            id=task_id,
            creator_id=user_id,
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            status=TaskStatusEnum.DRAFT,
        )

        task_service.get_task = AsyncMock(return_value=existing_task)

        update_data = TaskUpdate(budget=Decimal("5.00"))

        task = await task_service.update_task(task_id, user_id, update_data)

        assert task is not None
        assert task.budget == Decimal("5.00")
        assert task.service_fee == Decimal("0.75")  # 15% of 5.00
        assert task.total_cost == Decimal("5.75")

    async def test_update_task_not_found(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test updating non-existent task."""
        task_service.get_task = AsyncMock(return_value=None)

        update_data = TaskUpdate(title="Updated Title")

        task = await task_service.update_task("nonexistent", "user-123", update_data)

        assert task is None


class TestTaskServiceDelete:
    """Tests for deleting tasks."""

    async def test_delete_task_success(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test successful task deletion."""
        task_id = "task-123"
        user_id = "user-123"

        existing_task = Task(
            id=task_id,
            creator_id=user_id,
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            status=TaskStatusEnum.DRAFT,
        )

        task_service.get_task = AsyncMock(return_value=existing_task)

        success = await task_service.delete_task(task_id, user_id)

        assert success is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_delete_task_not_found(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test deleting non-existent task."""
        task_service.get_task = AsyncMock(return_value=None)

        success = await task_service.delete_task("nonexistent", "user-123")

        assert success is False
        mock_session.delete.assert_not_called()


class TestTaskServiceList:
    """Tests for listing tasks."""

    async def test_list_tasks_with_pagination(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test listing tasks with pagination."""
        mock_tasks = [
            Task(
                id=f"task-{i}",
                creator_id="user-123",
                title=f"Task {i}",
                description="Test description",
                instructions="Test instructions",
                platform=PlatformEnum.INSTAGRAM,
                task_type=TaskTypeEnum.LIKE,
                budget=Decimal("1.00"),
                service_fee=Decimal("0.15"),
                total_cost=Decimal("1.15"),
                max_performers=10,
                status=TaskStatusEnum.ACTIVE,
            )
            for i in range(5)
        ]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 5

        # Mock data query
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = mock_tasks

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total = await task_service.list_tasks(skip=0, limit=20)

        assert len(tasks) == 5
        assert total == 5
        assert tasks[0].title == "Task 0"

    async def test_list_tasks_with_filters(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test listing tasks with filters."""
        # Mock responses
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total = await task_service.list_tasks(
            skip=0,
            limit=20,
            creator_id="user-123",
            status=TaskStatusEnum.ACTIVE,
            platform="instagram",
        )

        assert total == 2
        assert mock_session.execute.call_count == 2

    async def test_list_tasks_with_search(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test listing tasks with search."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total = await task_service.list_tasks(skip=0, limit=20, search="instagram")

        assert total == 1


class TestServiceFeeCalculation:
    """Tests for service fee calculation."""

    async def test_calculate_service_fee(
        self, task_service: TaskService
    ) -> None:
        """Test service fee calculation."""
        result = await task_service.calculate_service_fee(Decimal("10.00"))

        assert result["budget"] == Decimal("10.00")
        assert result["service_fee"] == Decimal("1.50")  # 15%
        assert result["total_cost"] == Decimal("11.50")

    async def test_calculate_service_fee_rounding(
        self, task_service: TaskService
    ) -> None:
        """Test service fee rounding to 2 decimals."""
        result = await task_service.calculate_service_fee(Decimal("0.33"))

        assert result["budget"] == Decimal("0.33")
        assert result["service_fee"] == Decimal("0.05")  # 0.0495 rounded to 0.05
        assert result["total_cost"] == Decimal("0.38")


class TestGetCreatorTasks:
    """Tests for getting creator's tasks."""

    async def test_get_creator_tasks(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test getting tasks by creator."""
        # Mock list_tasks
        task_service.list_tasks = AsyncMock(return_value=([], 0))

        tasks, total = await task_service.get_creator_tasks("user-123", skip=0, limit=20)

        task_service.list_tasks.assert_called_once_with(
            skip=0, limit=20, creator_id="user-123"
        )


class TestGetActiveTasks:
    """Tests for getting active tasks."""

    async def test_get_active_tasks(
        self, task_service: TaskService, mock_session: AsyncMock
    ) -> None:
        """Test getting active tasks."""
        # Mock list_tasks
        task_service.list_tasks = AsyncMock(return_value=([], 0))

        tasks, total = await task_service.get_active_tasks(skip=0, limit=20)

        task_service.list_tasks.assert_called_once_with(
            skip=0, limit=20, status=TaskStatusEnum.ACTIVE
        )
