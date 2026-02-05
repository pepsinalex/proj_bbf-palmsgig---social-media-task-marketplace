"""
Tests for DiscoveryService.

Comprehensive tests for task discovery service including filtering,
pagination, searching, and query building functionality.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.schemas.discovery import (
    PaginationParams,
    TaskDiscoveryResponse,
    TaskFilter,
    TaskSearch,
)
from src.task_management.services.discovery_service import DiscoveryService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def discovery_service(mock_session: AsyncMock) -> DiscoveryService:
    """Create DiscoveryService instance with mock session."""
    return DiscoveryService(mock_session)


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-123",
        creator_id="user-456",
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
        target_criteria={"countries": ["US", "CA"], "min_age": 18},
        expires_at=datetime.utcnow() + timedelta(days=7),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_tasks() -> list[Task]:
    """Create multiple sample tasks for testing."""
    now = datetime.utcnow()
    return [
        Task(
            id=f"task-{i}",
            creator_id=f"user-{i}",
            title=f"Task {i}",
            description=f"Description {i}",
            instructions=f"Instructions {i}",
            platform=PlatformEnum.INSTAGRAM if i % 2 == 0 else PlatformEnum.FACEBOOK,
            task_type=TaskTypeEnum.LIKE if i % 2 == 0 else TaskTypeEnum.FOLLOW,
            budget=Decimal(f"{i}.00"),
            service_fee=Decimal(f"{i * 0.15:.2f}"),
            total_cost=Decimal(f"{i * 1.15:.2f}"),
            max_performers=100,
            current_performers=i * 10,
            status=TaskStatusEnum.ACTIVE,
            target_criteria={},
            expires_at=now + timedelta(days=i),
            created_at=now - timedelta(hours=i),
            updated_at=now,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def default_filters() -> TaskFilter:
    """Create default task filters."""
    return TaskFilter()


@pytest.fixture
def default_pagination() -> PaginationParams:
    """Create default pagination params."""
    return PaginationParams()


class TestDiscoveryServiceInitialization:
    """Tests for DiscoveryService initialization."""

    def test_initialization_success(self, mock_session: AsyncMock) -> None:
        """Test successful DiscoveryService initialization."""
        service = DiscoveryService(mock_session)

        assert service.db_session == mock_session


class TestGetAvailableTasks:
    """Tests for get_available_tasks method."""

    async def test_get_available_tasks_success(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_tasks: list[Task],
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test successful retrieval of available tasks."""
        # Mock count query result
        count_result = MagicMock()
        count_result.scalar_one.return_value = len(sample_tasks)

        # Mock data query result
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = sample_tasks

        # Setup execute to return different results for count vs data queries
        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.get_available_tasks(
            filters=default_filters, pagination=default_pagination
        )

        assert len(tasks) == len(sample_tasks)
        assert total_count == len(sample_tasks)
        assert isinstance(tasks[0], TaskDiscoveryResponse)
        assert tasks[0].id == sample_tasks[0].id
        assert tasks[0].title == sample_tasks[0].title

    async def test_get_available_tasks_empty_result(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test get_available_tasks with no results."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.get_available_tasks(
            filters=default_filters, pagination=default_pagination
        )

        assert len(tasks) == 0
        assert total_count == 0

    async def test_get_available_tasks_with_pagination(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_tasks: list[Task],
        default_filters: TaskFilter,
    ) -> None:
        """Test get_available_tasks with custom pagination."""
        pagination = PaginationParams(page=2, page_size=2)

        count_result = MagicMock()
        count_result.scalar_one.return_value = len(sample_tasks)

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = sample_tasks[2:4]

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.get_available_tasks(
            filters=default_filters, pagination=pagination
        )

        assert len(tasks) == 2
        assert total_count == len(sample_tasks)

    async def test_get_available_tasks_handles_error(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test get_available_tasks handles database errors."""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await discovery_service.get_available_tasks(
                filters=default_filters, pagination=default_pagination
            )


class TestSearchTasks:
    """Tests for search_tasks method."""

    async def test_search_tasks_success(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_tasks: list[Task],
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test successful task search."""
        search_params = TaskSearch(query="Instagram")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        data_result = MagicMock()
        matching_tasks = [t for t in sample_tasks if t.platform == PlatformEnum.INSTAGRAM]
        data_result.scalars.return_value.all.return_value = matching_tasks

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.search_tasks(
            search_params=search_params,
            filters=default_filters,
            pagination=default_pagination,
        )

        assert len(tasks) == len(matching_tasks)
        assert total_count == 2
        assert isinstance(tasks[0], TaskDiscoveryResponse)

    async def test_search_tasks_with_all_fields(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_tasks: list[Task],
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test search across all text fields."""
        search_params = TaskSearch(
            query="test", search_fields=["title", "description", "instructions"]
        )

        count_result = MagicMock()
        count_result.scalar_one.return_value = 3

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = sample_tasks[:3]

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.search_tasks(
            search_params=search_params,
            filters=default_filters,
            pagination=default_pagination,
        )

        assert len(tasks) == 3
        assert total_count == 3

    async def test_search_tasks_single_field(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_tasks: list[Task],
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test search in single field only."""
        search_params = TaskSearch(query="Task", search_fields=["title"])

        count_result = MagicMock()
        count_result.scalar_one.return_value = 5

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = sample_tasks

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.search_tasks(
            search_params=search_params,
            filters=default_filters,
            pagination=default_pagination,
        )

        assert len(tasks) == 5

    async def test_search_tasks_empty_results(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test search with no matching results."""
        search_params = TaskSearch(query="nonexistent")

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, data_result]

        tasks, total_count = await discovery_service.search_tasks(
            search_params=search_params,
            filters=default_filters,
            pagination=default_pagination,
        )

        assert len(tasks) == 0
        assert total_count == 0

    async def test_search_tasks_handles_error(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
        default_pagination: PaginationParams,
    ) -> None:
        """Test search_tasks handles errors."""
        search_params = TaskSearch(query="test")

        mock_session.execute.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="Search failed"):
            await discovery_service.search_tasks(
                search_params=search_params,
                filters=default_filters,
                pagination=default_pagination,
            )


class TestApplyFilters:
    """Tests for _apply_filters method."""

    def test_apply_filters_platform(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying platform filter."""
        query = select(Task)
        filters = TaskFilter(platform=PlatformEnum.INSTAGRAM)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_task_type(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying task_type filter."""
        query = select(Task)
        filters = TaskFilter(task_type=TaskTypeEnum.LIKE)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_status(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying status filter."""
        query = select(Task)
        filters = TaskFilter(status=TaskStatusEnum.ACTIVE)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_default_active_status(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test default ACTIVE status filter when not specified."""
        query = select(Task)
        filters = TaskFilter()

        filtered_query = discovery_service._apply_filters(query, filters)

        # Should apply ACTIVE status by default
        assert filtered_query is not None

    def test_apply_filters_budget_range(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying budget range filters."""
        query = select(Task)
        filters = TaskFilter(min_budget=Decimal("5.00"), max_budget=Decimal("20.00"))

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_min_budget_only(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying min_budget filter only."""
        query = select(Task)
        filters = TaskFilter(min_budget=Decimal("10.00"))

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_max_budget_only(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying max_budget filter only."""
        query = select(Task)
        filters = TaskFilter(max_budget=Decimal("50.00"))

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_creator_id(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying creator_id filter."""
        query = select(Task)
        filters = TaskFilter(creator_id="user-123")

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_exclude_expired(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test exclude_expired filter."""
        query = select(Task)
        filters = TaskFilter(exclude_expired=True)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_include_expired(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test including expired tasks."""
        query = select(Task)
        filters = TaskFilter(exclude_expired=False)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_exclude_full(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test exclude_full filter."""
        query = select(Task)
        filters = TaskFilter(exclude_full=True)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_include_full(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test including full tasks."""
        query = select(Task)
        filters = TaskFilter(exclude_full=False)

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None

    def test_apply_filters_multiple_conditions(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test applying multiple filters together."""
        query = select(Task)
        filters = TaskFilter(
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            min_budget=Decimal("5.00"),
            max_budget=Decimal("20.00"),
            exclude_expired=True,
            exclude_full=True,
        )

        filtered_query = discovery_service._apply_filters(query, filters)

        assert filtered_query is not None


class TestApplySorting:
    """Tests for _apply_sorting method."""

    def test_apply_sorting_created_at_desc(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by created_at descending."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "created_at", "desc")

        assert sorted_query is not None

    def test_apply_sorting_created_at_asc(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by created_at ascending."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "created_at", "asc")

        assert sorted_query is not None

    def test_apply_sorting_budget_desc(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by budget descending."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "budget", "desc")

        assert sorted_query is not None

    def test_apply_sorting_budget_asc(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by budget ascending."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "budget", "asc")

        assert sorted_query is not None

    def test_apply_sorting_expires_at(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by expires_at."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "expires_at", "asc")

        assert sorted_query is not None

    def test_apply_sorting_current_performers(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting by current_performers."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(
            query, "current_performers", "desc"
        )

        assert sorted_query is not None

    def test_apply_sorting_invalid_field_defaults_to_created_at(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test invalid sort field defaults to created_at."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "invalid_field", "desc")

        assert sorted_query is not None

    def test_apply_sorting_case_insensitive_order(
        self, discovery_service: DiscoveryService
    ) -> None:
        """Test sorting order is case insensitive."""
        query = select(Task)

        sorted_query = discovery_service._apply_sorting(query, "budget", "DESC")

        assert sorted_query is not None


class TestGetTaskById:
    """Tests for get_task_by_id method."""

    async def test_get_task_by_id_success(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        sample_task: Task,
    ) -> None:
        """Test successful task retrieval by ID."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_task

        mock_session.execute.return_value = result

        task = await discovery_service.get_task_by_id(sample_task.id)

        assert task is not None
        assert isinstance(task, TaskDiscoveryResponse)
        assert task.id == sample_task.id
        assert task.title == sample_task.title
        assert task.platform == sample_task.platform

    async def test_get_task_by_id_not_found(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_task_by_id returns None when task not found."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = result

        task = await discovery_service.get_task_by_id("nonexistent-id")

        assert task is None

    async def test_get_task_by_id_handles_error(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_task_by_id handles database errors."""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await discovery_service.get_task_by_id("task-123")


class TestGetTaskCountByFilters:
    """Tests for get_task_count_by_filters method."""

    async def test_get_task_count_success(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
    ) -> None:
        """Test successful task count retrieval."""
        result = MagicMock()
        result.scalar_one.return_value = 42

        mock_session.execute.return_value = result

        count = await discovery_service.get_task_count_by_filters(default_filters)

        assert count == 42

    async def test_get_task_count_zero(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
    ) -> None:
        """Test task count returns zero for no matches."""
        result = MagicMock()
        result.scalar_one.return_value = 0

        mock_session.execute.return_value = result

        count = await discovery_service.get_task_count_by_filters(default_filters)

        assert count == 0

    async def test_get_task_count_with_filters(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
    ) -> None:
        """Test task count with specific filters."""
        filters = TaskFilter(
            platform=PlatformEnum.INSTAGRAM, task_type=TaskTypeEnum.LIKE
        )

        result = MagicMock()
        result.scalar_one.return_value = 15

        mock_session.execute.return_value = result

        count = await discovery_service.get_task_count_by_filters(filters)

        assert count == 15

    async def test_get_task_count_handles_error(
        self,
        discovery_service: DiscoveryService,
        mock_session: AsyncMock,
        default_filters: TaskFilter,
    ) -> None:
        """Test get_task_count_by_filters handles errors."""
        mock_session.execute.side_effect = Exception("Count failed")

        with pytest.raises(Exception, match="Count failed"):
            await discovery_service.get_task_count_by_filters(default_filters)


class TestPaginationParams:
    """Tests for PaginationParams schema."""

    def test_pagination_default_values(self) -> None:
        """Test PaginationParams default values."""
        pagination = PaginationParams()

        assert pagination.page == 1
        assert pagination.page_size == 20

    def test_pagination_custom_values(self) -> None:
        """Test PaginationParams with custom values."""
        pagination = PaginationParams(page=3, page_size=50)

        assert pagination.page == 3
        assert pagination.page_size == 50

    def test_pagination_offset_calculation(self) -> None:
        """Test offset calculation from page and page_size."""
        pagination = PaginationParams(page=1, page_size=20)
        assert pagination.offset == 0

        pagination = PaginationParams(page=2, page_size=20)
        assert pagination.offset == 20

        pagination = PaginationParams(page=3, page_size=10)
        assert pagination.offset == 20

        pagination = PaginationParams(page=5, page_size=25)
        assert pagination.offset == 100

    def test_pagination_validates_page_minimum(self) -> None:
        """Test page must be at least 1."""
        with pytest.raises(ValueError):
            PaginationParams(page=0)

        with pytest.raises(ValueError):
            PaginationParams(page=-1)

    def test_pagination_validates_page_size_minimum(self) -> None:
        """Test page_size must be at least 1."""
        with pytest.raises(ValueError):
            PaginationParams(page_size=0)

        with pytest.raises(ValueError):
            PaginationParams(page_size=-1)

    def test_pagination_validates_page_size_maximum(self) -> None:
        """Test page_size must not exceed 100."""
        with pytest.raises(ValueError):
            PaginationParams(page_size=101)

        with pytest.raises(ValueError):
            PaginationParams(page_size=1000)

    def test_pagination_allows_max_page_size(self) -> None:
        """Test page_size of 100 is allowed."""
        pagination = PaginationParams(page_size=100)
        assert pagination.page_size == 100
