"""
Tests for Task State Machine Service.

Comprehensive tests for TaskStateMachine including state transitions,
validation, history tracking, and automation logic.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import TaskStatusEnum
from src.task_management.models.task import Task, PlatformEnum, TaskTypeEnum
from src.task_management.models.task_history import TaskHistory
from src.task_management.services.state_machine import TaskStateMachine


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def state_machine(mock_session: AsyncSession) -> TaskStateMachine:
    """Create a TaskStateMachine instance."""
    return TaskStateMachine(mock_session)


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
        status=TaskStatusEnum.DRAFT,
    )


class TestStateTransitions:
    """Tests for state transition validation."""

    def test_draft_to_pending_payment_valid(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test valid transition from DRAFT to PENDING_PAYMENT."""
        assert state_machine.validate_transition(
            TaskStatusEnum.DRAFT, TaskStatusEnum.PENDING_PAYMENT
        )

    def test_draft_to_cancelled_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from DRAFT to CANCELLED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.DRAFT, TaskStatusEnum.CANCELLED
        )

    def test_draft_to_active_invalid(self, state_machine: TaskStateMachine) -> None:
        """Test invalid transition from DRAFT to ACTIVE."""
        assert not state_machine.validate_transition(
            TaskStatusEnum.DRAFT, TaskStatusEnum.ACTIVE
        )

    def test_pending_payment_to_active_valid(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test valid transition from PENDING_PAYMENT to ACTIVE."""
        assert state_machine.validate_transition(
            TaskStatusEnum.PENDING_PAYMENT, TaskStatusEnum.ACTIVE
        )

    def test_pending_payment_to_cancelled_valid(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test valid transition from PENDING_PAYMENT to CANCELLED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.PENDING_PAYMENT, TaskStatusEnum.CANCELLED
        )

    def test_active_to_paused_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from ACTIVE to PAUSED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.ACTIVE, TaskStatusEnum.PAUSED
        )

    def test_active_to_completed_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from ACTIVE to COMPLETED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.ACTIVE, TaskStatusEnum.COMPLETED
        )

    def test_active_to_expired_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from ACTIVE to EXPIRED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.ACTIVE, TaskStatusEnum.EXPIRED
        )

    def test_paused_to_active_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from PAUSED to ACTIVE."""
        assert state_machine.validate_transition(
            TaskStatusEnum.PAUSED, TaskStatusEnum.ACTIVE
        )

    def test_paused_to_expired_valid(self, state_machine: TaskStateMachine) -> None:
        """Test valid transition from PAUSED to EXPIRED."""
        assert state_machine.validate_transition(
            TaskStatusEnum.PAUSED, TaskStatusEnum.EXPIRED
        )

    def test_completed_no_valid_transitions(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test that COMPLETED is terminal state."""
        assert not state_machine.validate_transition(
            TaskStatusEnum.COMPLETED, TaskStatusEnum.ACTIVE
        )
        assert not state_machine.validate_transition(
            TaskStatusEnum.COMPLETED, TaskStatusEnum.CANCELLED
        )

    def test_cancelled_no_valid_transitions(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test that CANCELLED is terminal state."""
        assert not state_machine.validate_transition(
            TaskStatusEnum.CANCELLED, TaskStatusEnum.ACTIVE
        )
        assert not state_machine.validate_transition(
            TaskStatusEnum.CANCELLED, TaskStatusEnum.COMPLETED
        )

    def test_expired_no_valid_transitions(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test that EXPIRED is terminal state."""
        assert not state_machine.validate_transition(
            TaskStatusEnum.EXPIRED, TaskStatusEnum.ACTIVE
        )
        assert not state_machine.validate_transition(
            TaskStatusEnum.EXPIRED, TaskStatusEnum.PAUSED
        )


class TestCanTransition:
    """Tests for can_transition method."""

    def test_can_transition_alias_for_validate(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test that can_transition is alias for validate_transition."""
        assert state_machine.can_transition(
            TaskStatusEnum.DRAFT, TaskStatusEnum.PENDING_PAYMENT
        )
        assert not state_machine.can_transition(
            TaskStatusEnum.DRAFT, TaskStatusEnum.ACTIVE
        )


class TestGetValidTransitions:
    """Tests for get_valid_transitions method."""

    def test_get_valid_transitions_draft(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test getting valid transitions from DRAFT."""
        valid = state_machine.get_valid_transitions(TaskStatusEnum.DRAFT)
        assert TaskStatusEnum.PENDING_PAYMENT in valid
        assert TaskStatusEnum.CANCELLED in valid
        assert TaskStatusEnum.ACTIVE not in valid

    def test_get_valid_transitions_active(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test getting valid transitions from ACTIVE."""
        valid = state_machine.get_valid_transitions(TaskStatusEnum.ACTIVE)
        assert TaskStatusEnum.PAUSED in valid
        assert TaskStatusEnum.COMPLETED in valid
        assert TaskStatusEnum.CANCELLED in valid
        assert TaskStatusEnum.EXPIRED in valid
        assert TaskStatusEnum.DRAFT not in valid

    def test_get_valid_transitions_completed(
        self, state_machine: TaskStateMachine
    ) -> None:
        """Test getting valid transitions from COMPLETED."""
        valid = state_machine.get_valid_transitions(TaskStatusEnum.COMPLETED)
        assert len(valid) == 0


class TestTransitionTask:
    """Tests for transition_task method."""

    @pytest.mark.asyncio
    async def test_transition_task_success(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test successful task transition."""
        sample_task.status = TaskStatusEnum.DRAFT
        previous_status = sample_task.status

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=previous_status.value,
                new_status=TaskStatusEnum.PENDING_PAYMENT.value,
                changed_by="user-456",
            )
            mock_create_entry.return_value = mock_history

            result = await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.PENDING_PAYMENT,
                changed_by="user-456",
                reason="Payment initiated",
            )

            assert result is True
            assert sample_task.status == TaskStatusEnum.PENDING_PAYMENT
            state_machine.session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_task_invalid_transition(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test transition with invalid state change."""
        sample_task.status = TaskStatusEnum.DRAFT

        with pytest.raises(ValueError, match="Invalid transition"):
            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.ACTIVE,
                changed_by="user-456",
            )

    @pytest.mark.asyncio
    async def test_transition_task_with_metadata(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test transition with metadata."""
        sample_task.status = TaskStatusEnum.ACTIVE
        metadata = {"reason": "Task completed successfully", "rating": 5}

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.ACTIVE.value,
                new_status=TaskStatusEnum.COMPLETED.value,
                changed_by="user-456",
                metadata=metadata,
            )
            mock_create_entry.return_value = mock_history

            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.COMPLETED,
                changed_by="user-456",
                metadata=metadata,
            )

            assert sample_task.status == TaskStatusEnum.COMPLETED


class TestTransitionLogic:
    """Tests for automatic transition logic."""

    @pytest.mark.asyncio
    async def test_active_transition_sets_expiration(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test that transitioning to ACTIVE sets expires_at."""
        sample_task.status = TaskStatusEnum.PENDING_PAYMENT
        sample_task.expires_at = None

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.PENDING_PAYMENT.value,
                new_status=TaskStatusEnum.ACTIVE.value,
                changed_by="system",
            )
            mock_create_entry.return_value = mock_history

            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.ACTIVE,
                changed_by="system",
            )

            assert sample_task.expires_at is not None
            assert sample_task.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_active_transition_preserves_existing_expiration(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test that existing expires_at is preserved."""
        sample_task.status = TaskStatusEnum.PENDING_PAYMENT
        existing_expiration = datetime.utcnow() + timedelta(days=14)
        sample_task.expires_at = existing_expiration

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.PENDING_PAYMENT.value,
                new_status=TaskStatusEnum.ACTIVE.value,
                changed_by="system",
            )
            mock_create_entry.return_value = mock_history

            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.ACTIVE,
                changed_by="system",
            )

            assert sample_task.expires_at == existing_expiration

    @pytest.mark.asyncio
    async def test_paused_transition_clears_expiration(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test that transitioning to PAUSED clears expires_at."""
        sample_task.status = TaskStatusEnum.ACTIVE
        sample_task.expires_at = datetime.utcnow() + timedelta(days=7)

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.ACTIVE.value,
                new_status=TaskStatusEnum.PAUSED.value,
                changed_by="user-123",
            )
            mock_create_entry.return_value = mock_history

            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.PAUSED,
                changed_by="user-123",
            )

            assert sample_task.expires_at is None

    @pytest.mark.asyncio
    async def test_completed_transition_clears_expiration(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test that transitioning to COMPLETED clears expires_at."""
        sample_task.status = TaskStatusEnum.ACTIVE
        sample_task.expires_at = datetime.utcnow() + timedelta(days=7)

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            mock_history = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.ACTIVE.value,
                new_status=TaskStatusEnum.COMPLETED.value,
                changed_by="system",
            )
            mock_create_entry.return_value = mock_history

            await state_machine.transition_task(
                task=sample_task,
                new_status=TaskStatusEnum.COMPLETED,
                changed_by="system",
            )

            assert sample_task.expires_at is None


class TestStateMachineIntegration:
    """Integration tests for state machine."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_draft_to_completed(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test complete lifecycle from DRAFT to COMPLETED."""
        sample_task.status = TaskStatusEnum.DRAFT

        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            # DRAFT -> PENDING_PAYMENT
            mock_create_entry.return_value = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.DRAFT.value,
                new_status=TaskStatusEnum.PENDING_PAYMENT.value,
                changed_by="user-123",
            )
            await state_machine.transition_task(
                sample_task, TaskStatusEnum.PENDING_PAYMENT, "user-123"
            )
            assert sample_task.status == TaskStatusEnum.PENDING_PAYMENT

            # PENDING_PAYMENT -> ACTIVE
            mock_create_entry.return_value = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.PENDING_PAYMENT.value,
                new_status=TaskStatusEnum.ACTIVE.value,
                changed_by="system",
            )
            await state_machine.transition_task(
                sample_task, TaskStatusEnum.ACTIVE, "system"
            )
            assert sample_task.status == TaskStatusEnum.ACTIVE
            assert sample_task.expires_at is not None

            # ACTIVE -> COMPLETED
            mock_create_entry.return_value = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.ACTIVE.value,
                new_status=TaskStatusEnum.COMPLETED.value,
                changed_by="system",
            )
            await state_machine.transition_task(
                sample_task, TaskStatusEnum.COMPLETED, "system"
            )
            assert sample_task.status == TaskStatusEnum.COMPLETED
            assert sample_task.expires_at is None

    @pytest.mark.asyncio
    async def test_cancellation_from_various_states(
        self, state_machine: TaskStateMachine, sample_task: Task
    ) -> None:
        """Test that cancellation works from multiple states."""
        with patch.object(TaskHistory, "create_entry") as mock_create_entry:
            # Cancel from DRAFT
            sample_task.status = TaskStatusEnum.DRAFT
            mock_create_entry.return_value = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.DRAFT.value,
                new_status=TaskStatusEnum.CANCELLED.value,
                changed_by="user-123",
            )
            await state_machine.transition_task(
                sample_task, TaskStatusEnum.CANCELLED, "user-123"
            )
            assert sample_task.status == TaskStatusEnum.CANCELLED

            # Reset and cancel from ACTIVE
            sample_task.status = TaskStatusEnum.ACTIVE
            mock_create_entry.return_value = TaskHistory(
                task_id=sample_task.id,
                previous_status=TaskStatusEnum.ACTIVE.value,
                new_status=TaskStatusEnum.CANCELLED.value,
                changed_by="user-123",
            )
            await state_machine.transition_task(
                sample_task, TaskStatusEnum.CANCELLED, "user-123"
            )
            assert sample_task.status == TaskStatusEnum.CANCELLED
