"""
Tests for Task Expiration Service.

Comprehensive tests for ExpirationService including expiration checks,
cleanup operations, and automated task lifecycle management.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)
from src.task_management.services.expiration_service import (
    ASSIGNMENT_EXPIRATION_HOURS,
    COMPLETION_EXPIRATION_HOURS,
    ExpirationService,
)


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def expiration_service(mock_session: AsyncSession) -> ExpirationService:
    """Create an ExpirationService instance."""
    return ExpirationService(mock_session)


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


class TestCheckExpiredTasks:
    """Tests for check_expired_tasks method."""

    @pytest.mark.asyncio
    async def test_check_expired_tasks_finds_expired(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test finding expired tasks."""
        # Set task to be expired
        sample_task.expires_at = datetime.utcnow() - timedelta(hours=1)

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        expired_tasks = await expiration_service.check_expired_tasks()

        assert len(expired_tasks) == 1
        assert expired_tasks[0].id == sample_task.id

    @pytest.mark.asyncio
    async def test_check_expired_tasks_no_expired(
        self, expiration_service: ExpirationService
    ) -> None:
        """Test when no tasks are expired."""
        # Mock database response with empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expiration_service.session.execute.return_value = mock_result

        expired_tasks = await expiration_service.check_expired_tasks()

        assert len(expired_tasks) == 0

    @pytest.mark.asyncio
    async def test_check_expired_tasks_multiple(
        self, expiration_service: ExpirationService
    ) -> None:
        """Test finding multiple expired tasks."""
        # Create multiple expired tasks
        expired_tasks_list = [
            Task(
                id=f"task-{i}",
                creator_id="user-123",
                title=f"Task {i}",
                description="Test",
                instructions="Test",
                platform=PlatformEnum.INSTAGRAM,
                task_type=TaskTypeEnum.LIKE,
                budget=Decimal("1.00"),
                service_fee=Decimal("0.15"),
                total_cost=Decimal("1.15"),
                max_performers=10,
                status=TaskStatusEnum.ACTIVE,
                expires_at=datetime.utcnow() - timedelta(hours=i + 1),
            )
            for i in range(3)
        ]

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expired_tasks_list
        expiration_service.session.execute.return_value = mock_result

        expired_tasks = await expiration_service.check_expired_tasks()

        assert len(expired_tasks) == 3


class TestExpireUnassignedTasks:
    """Tests for expire_unassigned_tasks method."""

    @pytest.mark.asyncio
    async def test_expire_unassigned_tasks_default_age(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test expiring unassigned tasks with default age."""
        # Set task to be old and unassigned
        sample_task.created_at = datetime.utcnow() - timedelta(days=31)
        sample_task.current_performers = 0

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_unassigned_tasks()

            assert count == 1
            mock_sm_instance.transition_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_unassigned_tasks_custom_age(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test expiring unassigned tasks with custom age."""
        max_age_days = 14
        sample_task.created_at = datetime.utcnow() - timedelta(days=15)
        sample_task.current_performers = 0

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_unassigned_tasks(
                max_age_days=max_age_days
            )

            assert count == 1

    @pytest.mark.asyncio
    async def test_expire_unassigned_tasks_handles_error(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test handling errors during expiration."""
        sample_task.created_at = datetime.utcnow() - timedelta(days=31)
        sample_task.current_performers = 0

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock state machine that raises error
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm_instance.transition_task.side_effect = Exception("Transition error")
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_unassigned_tasks()

            # Should return 0 due to error
            assert count == 0

    @pytest.mark.asyncio
    async def test_expire_unassigned_tasks_ignores_assigned(
        self, expiration_service: ExpirationService
    ) -> None:
        """Test that tasks with assignments are not expired."""
        # Mock database response with empty list (no unassigned tasks)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expiration_service.session.execute.return_value = mock_result

        count = await expiration_service.expire_unassigned_tasks()

        assert count == 0


class TestExpireIncompleteTasks:
    """Tests for expire_incomplete_tasks method."""

    @pytest.mark.asyncio
    async def test_expire_incomplete_tasks_default_hours(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test expiring incomplete tasks with default hours."""
        # Set task to be old and incomplete
        sample_task.created_at = datetime.utcnow() - timedelta(
            hours=COMPLETION_EXPIRATION_HOURS + 1
        )
        sample_task.current_performers = 1
        sample_task.max_performers = 10

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock no recent activity
        expiration_service._has_recent_assignment_activity = AsyncMock(
            return_value=False
        )

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_incomplete_tasks()

            assert count == 1
            mock_sm_instance.transition_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_incomplete_tasks_custom_hours(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test expiring incomplete tasks with custom hours."""
        completion_hours = 24
        sample_task.created_at = datetime.utcnow() - timedelta(hours=25)
        sample_task.current_performers = 1
        sample_task.max_performers = 10

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock no recent activity
        expiration_service._has_recent_assignment_activity = AsyncMock(
            return_value=False
        )

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_incomplete_tasks(
                completion_hours=completion_hours
            )

            assert count == 1

    @pytest.mark.asyncio
    async def test_expire_incomplete_tasks_with_recent_activity(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test that tasks with recent activity are not expired."""
        sample_task.created_at = datetime.utcnow() - timedelta(hours=50)
        sample_task.current_performers = 1
        sample_task.max_performers = 10

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock recent activity exists
        expiration_service._has_recent_assignment_activity = AsyncMock(
            return_value=True
        )

        count = await expiration_service.expire_incomplete_tasks()

        # Should not expire due to recent activity
        assert count == 0

    @pytest.mark.asyncio
    async def test_expire_incomplete_tasks_handles_error(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test handling errors during incomplete task expiration."""
        sample_task.created_at = datetime.utcnow() - timedelta(hours=50)
        sample_task.current_performers = 1
        sample_task.max_performers = 10

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock no recent activity
        expiration_service._has_recent_assignment_activity = AsyncMock(
            return_value=False
        )

        # Mock state machine that raises error
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm_instance.transition_task.side_effect = Exception("Transition error")
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_incomplete_tasks()

            assert count == 0


class TestCleanupExpiredAssignments:
    """Tests for cleanup_expired_assignments method."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_assignments_default_hours(
        self,
        expiration_service: ExpirationService,
        sample_task: Task,
        sample_assignment: TaskAssignment,
    ) -> None:
        """Test cleaning up expired assignments with default hours."""
        # Set assignment to be old
        sample_assignment.assigned_at = datetime.utcnow() - timedelta(
            hours=ASSIGNMENT_EXPIRATION_HOURS + 1
        )
        sample_task.current_performers = 1

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_assignment]
        expiration_service.session.execute.return_value = mock_result

        # Mock get task
        expiration_service.session.get.return_value = sample_task

        count = await expiration_service.cleanup_expired_assignments()

        assert count == 1
        assert sample_assignment.status == AssignmentStatusEnum.CANCELLED
        assert sample_task.current_performers == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_assignments_custom_hours(
        self, expiration_service: ExpirationService, sample_assignment: TaskAssignment
    ) -> None:
        """Test cleaning up expired assignments with custom hours."""
        assignment_hours = 12
        sample_assignment.assigned_at = datetime.utcnow() - timedelta(hours=13)

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_assignment]
        expiration_service.session.execute.return_value = mock_result

        # Mock get task
        mock_task = MagicMock()
        mock_task.current_performers = 1
        expiration_service.session.get.return_value = mock_task

        count = await expiration_service.cleanup_expired_assignments(
            assignment_hours=assignment_hours
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_assignments_no_task(
        self, expiration_service: ExpirationService, sample_assignment: TaskAssignment
    ) -> None:
        """Test cleanup when task is not found."""
        sample_assignment.assigned_at = datetime.utcnow() - timedelta(hours=25)

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_assignment]
        expiration_service.session.execute.return_value = mock_result

        # Mock get task returns None
        expiration_service.session.get.return_value = None

        count = await expiration_service.cleanup_expired_assignments()

        # Should still count as cleaned up
        assert count == 1
        assert sample_assignment.status == AssignmentStatusEnum.CANCELLED

    @pytest.mark.asyncio
    async def test_cleanup_expired_assignments_handles_error(
        self, expiration_service: ExpirationService, sample_assignment: TaskAssignment
    ) -> None:
        """Test handling errors during cleanup."""
        sample_assignment.assigned_at = datetime.utcnow() - timedelta(hours=25)

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_assignment]
        expiration_service.session.execute.return_value = mock_result

        # Mock cancel raises error
        with patch.object(
            sample_assignment, "cancel", side_effect=Exception("Cancel error")
        ):
            count = await expiration_service.cleanup_expired_assignments()

            # Should return 0 due to error
            assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_assignments_multiple(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test cleaning up multiple expired assignments."""
        # Create multiple expired assignments
        assignments = [
            TaskAssignment(
                id=f"assignment-{i}",
                task_id=sample_task.id,
                performer_id=f"user-{i}",
                status=AssignmentStatusEnum.ASSIGNED,
                assigned_at=datetime.utcnow() - timedelta(hours=25 + i),
            )
            for i in range(3)
        ]
        sample_task.current_performers = 3

        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = assignments
        expiration_service.session.execute.return_value = mock_result

        # Mock get task
        expiration_service.session.get.return_value = sample_task

        count = await expiration_service.cleanup_expired_assignments()

        assert count == 3
        assert sample_task.current_performers == 0


class TestHasRecentAssignmentActivity:
    """Tests for _has_recent_assignment_activity method."""

    @pytest.mark.asyncio
    async def test_has_recent_activity_true(
        self, expiration_service: ExpirationService, sample_assignment: TaskAssignment
    ) -> None:
        """Test detecting recent activity."""
        task_id = "task-123"
        hours = 24

        # Mock recent assignment
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_assignment
        expiration_service.session.execute.return_value = mock_result

        has_activity = await expiration_service._has_recent_assignment_activity(
            task_id, hours
        )

        assert has_activity is True

    @pytest.mark.asyncio
    async def test_has_recent_activity_false(
        self, expiration_service: ExpirationService
    ) -> None:
        """Test when no recent activity."""
        task_id = "task-123"
        hours = 24

        # Mock no recent assignment
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expiration_service.session.execute.return_value = mock_result

        has_activity = await expiration_service._has_recent_assignment_activity(
            task_id, hours
        )

        assert has_activity is False


class TestExpirationServiceIntegration:
    """Integration tests for expiration service."""

    @pytest.mark.asyncio
    async def test_full_expiration_workflow(
        self, expiration_service: ExpirationService, sample_task: Task
    ) -> None:
        """Test complete expiration workflow."""
        # Setup old unassigned task
        sample_task.created_at = datetime.utcnow() - timedelta(days=31)
        sample_task.current_performers = 0

        # Mock database response for finding tasks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task]
        expiration_service.session.execute.return_value = mock_result

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            # Expire unassigned task
            count = await expiration_service.expire_unassigned_tasks()

            assert count == 1
            mock_sm_instance.transition_task.assert_called_once_with(
                task=sample_task,
                new_status=TaskStatusEnum.EXPIRED,
                changed_by="system",
                reason="Task expired: no assignments after 30 days",
            )

    @pytest.mark.asyncio
    async def test_expiration_service_handles_mixed_scenarios(
        self, expiration_service: ExpirationService
    ) -> None:
        """Test service handles mixed scenarios correctly."""
        # Create tasks with different scenarios
        old_unassigned = Task(
            id="task-1",
            creator_id="user-123",
            title="Old Unassigned",
            description="Test",
            instructions="Test",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            current_performers=0,
            status=TaskStatusEnum.ACTIVE,
            created_at=datetime.utcnow() - timedelta(days=31),
        )

        recent_unassigned = Task(
            id="task-2",
            creator_id="user-123",
            title="Recent Unassigned",
            description="Test",
            instructions="Test",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            current_performers=0,
            status=TaskStatusEnum.ACTIVE,
            created_at=datetime.utcnow() - timedelta(days=5),
        )

        # Mock database returns only old task
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [old_unassigned]
        expiration_service.session.execute.return_value = mock_result

        # Mock state machine
        with patch(
            "src.task_management.services.expiration_service.TaskStateMachine"
        ) as mock_sm:
            mock_sm_instance = AsyncMock()
            mock_sm.return_value = mock_sm_instance

            count = await expiration_service.expire_unassigned_tasks()

            # Only old task should be expired
            assert count == 1
