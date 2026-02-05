"""
Tests for Task Assignment Service.

Comprehensive tests for AssignmentService including eligibility validation,
concurrent task limits, and assignment operations.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)
from src.task_management.services.assignment_service import (
    AssignmentService,
    MAX_CONCURRENT_TASKS,
    MIN_RATING_FOR_ASSIGNMENT,
)


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def assignment_service(mock_session: AsyncSession) -> AssignmentService:
    """Create an AssignmentService instance."""
    return AssignmentService(mock_session)


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    task = Task(
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
    )
    return task


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


class TestValidatePerformerEligibility:
    """Tests for validate_performer_eligibility method."""

    @pytest.mark.asyncio
    async def test_eligible_performer(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test performer is eligible when all validations pass."""
        performer_id = "user-456"

        # Mock no existing assignment
        assignment_service.session.scalar.return_value = None

        # Mock concurrent tasks count (below limit)
        assignment_service._count_concurrent_tasks = AsyncMock(return_value=2)

        # Mock social account exists
        assignment_service._check_social_account_exists = AsyncMock(return_value=True)

        is_eligible, error_msg = await assignment_service.validate_performer_eligibility(
            performer_id, sample_task
        )

        assert is_eligible is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_task_not_accepting_performers(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test validation fails when task cannot accept performers."""
        performer_id = "user-456"
        sample_task.current_performers = sample_task.max_performers

        is_eligible, error_msg = await assignment_service.validate_performer_eligibility(
            performer_id, sample_task
        )

        assert is_eligible is False
        assert "not accepting" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_performer_already_assigned(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test validation fails when performer already assigned."""
        performer_id = "user-456"

        # Mock existing assignment
        existing_assignment = TaskAssignment(
            id="assignment-789",
            task_id=sample_task.id,
            performer_id=performer_id,
            status=AssignmentStatusEnum.ASSIGNED,
        )
        assignment_service.session.scalar.return_value = existing_assignment

        is_eligible, error_msg = await assignment_service.validate_performer_eligibility(
            performer_id, sample_task
        )

        assert is_eligible is False
        assert "already assigned" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_concurrent_task_limit_reached(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test validation fails when concurrent limit reached."""
        performer_id = "user-456"

        # Mock no existing assignment
        assignment_service.session.scalar.return_value = None

        # Mock concurrent tasks at limit
        assignment_service._count_concurrent_tasks = AsyncMock(
            return_value=MAX_CONCURRENT_TASKS
        )

        is_eligible, error_msg = await assignment_service.validate_performer_eligibility(
            performer_id, sample_task
        )

        assert is_eligible is False
        assert "maximum concurrent tasks" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_missing_social_account(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test validation fails when social account missing."""
        performer_id = "user-456"

        # Mock no existing assignment
        assignment_service.session.scalar.return_value = None

        # Mock concurrent tasks below limit
        assignment_service._count_concurrent_tasks = AsyncMock(return_value=2)

        # Mock social account does not exist
        assignment_service._check_social_account_exists = AsyncMock(return_value=False)

        is_eligible, error_msg = await assignment_service.validate_performer_eligibility(
            performer_id, sample_task
        )

        assert is_eligible is False
        assert sample_task.platform.value.lower() in error_msg.lower()


class TestCheckConcurrentLimits:
    """Tests for check_concurrent_limits method."""

    @pytest.mark.asyncio
    async def test_check_concurrent_limits_below_max(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test checking limits when below maximum."""
        performer_id = "user-456"
        assignment_service._count_concurrent_tasks = AsyncMock(return_value=3)

        current, max_allowed = await assignment_service.check_concurrent_limits(
            performer_id
        )

        assert current == 3
        assert max_allowed == MAX_CONCURRENT_TASKS

    @pytest.mark.asyncio
    async def test_check_concurrent_limits_at_max(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test checking limits when at maximum."""
        performer_id = "user-456"
        assignment_service._count_concurrent_tasks = AsyncMock(
            return_value=MAX_CONCURRENT_TASKS
        )

        current, max_allowed = await assignment_service.check_concurrent_limits(
            performer_id
        )

        assert current == MAX_CONCURRENT_TASKS
        assert max_allowed == MAX_CONCURRENT_TASKS


class TestAssignTask:
    """Tests for assign_task method."""

    @pytest.mark.asyncio
    async def test_assign_task_success(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test successful task assignment."""
        performer_id = "user-456"

        # Mock eligibility validation passes
        assignment_service.validate_performer_eligibility = AsyncMock(
            return_value=(True, None)
        )

        assignment, error_msg = await assignment_service.assign_task(
            sample_task, performer_id
        )

        assert assignment is not None
        assert error_msg is None
        assert assignment.task_id == sample_task.id
        assert assignment.performer_id == performer_id
        assert assignment.status == AssignmentStatusEnum.ASSIGNED
        assert sample_task.current_performers == 1
        assignment_service.session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_task_eligibility_fails(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test assignment fails when eligibility check fails."""
        performer_id = "user-456"

        # Mock eligibility validation fails
        assignment_service.validate_performer_eligibility = AsyncMock(
            return_value=(False, "Not eligible")
        )

        assignment, error_msg = await assignment_service.assign_task(
            sample_task, performer_id
        )

        assert assignment is None
        assert error_msg == "Not eligible"
        assert sample_task.current_performers == 0

    @pytest.mark.asyncio
    async def test_assign_task_exception_handling(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test assignment handles exceptions gracefully."""
        performer_id = "user-456"

        # Mock eligibility validation passes
        assignment_service.validate_performer_eligibility = AsyncMock(
            return_value=(True, None)
        )

        # Mock flush raises exception
        assignment_service.session.flush.side_effect = Exception("Database error")

        assignment, error_msg = await assignment_service.assign_task(
            sample_task, performer_id
        )

        assert assignment is None
        assert "failed" in error_msg.lower()


class TestUnassignTask:
    """Tests for unassign_task method."""

    @pytest.mark.asyncio
    async def test_unassign_task_success(
        self,
        assignment_service: AssignmentService,
        sample_task: Task,
        sample_assignment: TaskAssignment,
    ) -> None:
        """Test successful task unassignment."""
        sample_task.current_performers = 1

        # Mock get task
        assignment_service.session.get.return_value = sample_task

        success, error_msg = await assignment_service.unassign_task(sample_assignment)

        assert success is True
        assert error_msg is None
        assert sample_assignment.status == AssignmentStatusEnum.CANCELLED
        assert sample_task.current_performers == 0

    @pytest.mark.asyncio
    async def test_unassign_task_no_task_found(
        self, assignment_service: AssignmentService, sample_assignment: TaskAssignment
    ) -> None:
        """Test unassignment when task not found."""
        # Mock get task returns None
        assignment_service.session.get.return_value = None

        success, error_msg = await assignment_service.unassign_task(sample_assignment)

        # Should still succeed but log warning
        assert success is True
        assert sample_assignment.status == AssignmentStatusEnum.CANCELLED

    @pytest.mark.asyncio
    async def test_unassign_task_exception_handling(
        self, assignment_service: AssignmentService, sample_assignment: TaskAssignment
    ) -> None:
        """Test unassignment handles exceptions gracefully."""
        # Mock cancel raises exception
        with patch.object(
            sample_assignment, "cancel", side_effect=Exception("Cancel error")
        ):
            success, error_msg = await assignment_service.unassign_task(
                sample_assignment
            )

            assert success is False
            assert "failed" in error_msg.lower()


class TestGetUserAssignments:
    """Tests for get_user_assignments method."""

    @pytest.mark.asyncio
    async def test_get_user_assignments_no_filter(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test retrieving all user assignments."""
        performer_id = "user-456"

        # Mock assignments
        assignments = [
            TaskAssignment(
                id=f"assignment-{i}",
                task_id=f"task-{i}",
                performer_id=performer_id,
                status=AssignmentStatusEnum.ASSIGNED,
            )
            for i in range(3)
        ]

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = assignments
        assignment_service.session.execute.return_value = mock_result

        result = await assignment_service.get_user_assignments(performer_id)

        assert len(result) == 3
        assert all(a.performer_id == performer_id for a in result)

    @pytest.mark.asyncio
    async def test_get_user_assignments_with_status_filter(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test retrieving user assignments with status filter."""
        performer_id = "user-456"
        status_filter = AssignmentStatusEnum.STARTED

        # Mock assignments
        assignments = [
            TaskAssignment(
                id="assignment-1",
                task_id="task-1",
                performer_id=performer_id,
                status=AssignmentStatusEnum.STARTED,
            )
        ]

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = assignments
        assignment_service.session.execute.return_value = mock_result

        result = await assignment_service.get_user_assignments(
            performer_id, status=status_filter
        )

        assert len(result) == 1
        assert result[0].status == AssignmentStatusEnum.STARTED

    @pytest.mark.asyncio
    async def test_get_user_assignments_with_pagination(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test retrieving user assignments with pagination."""
        performer_id = "user-456"
        limit = 10
        offset = 5

        # Mock assignments
        assignments = [
            TaskAssignment(
                id=f"assignment-{i}",
                task_id=f"task-{i}",
                performer_id=performer_id,
                status=AssignmentStatusEnum.ASSIGNED,
            )
            for i in range(10)
        ]

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = assignments
        assignment_service.session.execute.return_value = mock_result

        result = await assignment_service.get_user_assignments(
            performer_id, limit=limit, offset=offset
        )

        assert len(result) == 10


class TestCountConcurrentTasks:
    """Tests for _count_concurrent_tasks method."""

    @pytest.mark.asyncio
    async def test_count_concurrent_tasks_zero(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test counting when no concurrent tasks."""
        performer_id = "user-456"

        # Mock zero count
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        assignment_service.session.execute.return_value = mock_result

        count = await assignment_service._count_concurrent_tasks(performer_id)

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_concurrent_tasks_multiple(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test counting multiple concurrent tasks."""
        performer_id = "user-456"

        # Mock count of 3
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        assignment_service.session.execute.return_value = mock_result

        count = await assignment_service._count_concurrent_tasks(performer_id)

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_concurrent_tasks_none_result(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test counting when result is None."""
        performer_id = "user-456"

        # Mock None result
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        assignment_service.session.execute.return_value = mock_result

        count = await assignment_service._count_concurrent_tasks(performer_id)

        assert count == 0


class TestCheckSocialAccountExists:
    """Tests for _check_social_account_exists method."""

    @pytest.mark.asyncio
    async def test_social_account_exists(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test when social account exists and is verified."""
        user_id = "user-456"
        platform = PlatformEnum.INSTAGRAM

        # Mock account exists
        mock_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        assignment_service.session.execute.return_value = mock_result

        exists = await assignment_service._check_social_account_exists(
            user_id, platform
        )

        assert exists is True

    @pytest.mark.asyncio
    async def test_social_account_not_exists(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test when social account does not exist."""
        user_id = "user-456"
        platform = PlatformEnum.INSTAGRAM

        # Mock account does not exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        assignment_service.session.execute.return_value = mock_result

        exists = await assignment_service._check_social_account_exists(
            user_id, platform
        )

        assert exists is False

    @pytest.mark.asyncio
    async def test_social_account_check_exception(
        self, assignment_service: AssignmentService
    ) -> None:
        """Test exception handling in social account check."""
        user_id = "user-456"
        platform = PlatformEnum.INSTAGRAM

        # Mock exception
        assignment_service.session.execute.side_effect = Exception("Database error")

        exists = await assignment_service._check_social_account_exists(
            user_id, platform
        )

        # Should return False on error
        assert exists is False


class TestAssignmentServiceIntegration:
    """Integration tests for assignment service."""

    @pytest.mark.asyncio
    async def test_full_assignment_workflow(
        self, assignment_service: AssignmentService, sample_task: Task
    ) -> None:
        """Test complete assignment workflow."""
        performer_id = "user-456"

        # Mock all dependencies for successful assignment
        assignment_service.session.scalar.return_value = None
        assignment_service._count_concurrent_tasks = AsyncMock(return_value=2)
        assignment_service._check_social_account_exists = AsyncMock(return_value=True)

        # Assign task
        assignment, error_msg = await assignment_service.assign_task(
            sample_task, performer_id
        )

        assert assignment is not None
        assert sample_task.current_performers == 1

        # Unassign task
        assignment_service.session.get.return_value = sample_task
        success, error_msg = await assignment_service.unassign_task(assignment)

        assert success is True
        assert sample_task.current_performers == 0
