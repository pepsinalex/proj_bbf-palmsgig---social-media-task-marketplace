"""
Tests for Task Management Models.

Comprehensive tests for Task, TaskAssignment, and TaskHistory models
including validation, relationships, and business logic.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.task_management.models.task import (
    PlatformEnum,
    Task,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.models.task_assignment import (
    AssignmentStatusEnum,
    TaskAssignment,
)
from src.task_management.models.task_history import TaskHistory


class TestTaskModel:
    """Tests for Task model."""

    def test_create_task(self) -> None:
        """Test creating a task instance."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Need 100 likes on my Instagram post",
            instructions="1. Visit the post\n2. Click like\n3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("0.50"),
            service_fee=Decimal("0.08"),
            total_cost=Decimal("0.58"),
            max_performers=100,
            current_performers=0,
            status=TaskStatusEnum.DRAFT,
        )

        assert task.creator_id == "user-123"
        assert task.title == "Like my post"
        assert task.platform == PlatformEnum.INSTAGRAM
        assert task.task_type == TaskTypeEnum.LIKE
        assert task.budget == Decimal("0.50")
        assert task.service_fee == Decimal("0.08")
        assert task.total_cost == Decimal("0.58")
        assert task.max_performers == 100
        assert task.current_performers == 0
        assert task.status == TaskStatusEnum.DRAFT

    def test_task_is_active(self) -> None:
        """Test is_active method."""
        task = Task(
            creator_id="user-123",
            title="Test",
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

        assert task.is_active() is True

        task.status = TaskStatusEnum.DRAFT
        assert task.is_active() is False

    def test_task_is_expired(self) -> None:
        """Test is_expired method."""
        # Task with no expiration
        task = Task(
            creator_id="user-123",
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            expires_at=None,
        )
        assert task.is_expired() is False

        # Task with future expiration
        task.expires_at = datetime.utcnow() + timedelta(days=7)
        assert task.is_expired() is False

        # Task with past expiration
        task.expires_at = datetime.utcnow() - timedelta(days=1)
        assert task.is_expired() is True

    def test_task_can_accept_performers(self) -> None:
        """Test can_accept_performers method."""
        task = Task(
            creator_id="user-123",
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            current_performers=5,
            status=TaskStatusEnum.ACTIVE,
        )

        assert task.can_accept_performers() is True

        # Max performers reached
        task.current_performers = 10
        assert task.can_accept_performers() is False

        # Not active
        task.current_performers = 5
        task.status = TaskStatusEnum.DRAFT
        assert task.can_accept_performers() is False

        # Expired
        task.status = TaskStatusEnum.ACTIVE
        task.expires_at = datetime.utcnow() - timedelta(days=1)
        assert task.can_accept_performers() is False

    def test_increment_performers(self) -> None:
        """Test increment_performers method."""
        task = Task(
            creator_id="user-123",
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            current_performers=5,
        )

        task.increment_performers()
        assert task.current_performers == 6

        # Test max limit
        task.current_performers = 10
        with pytest.raises(ValueError, match="Maximum performers limit reached"):
            task.increment_performers()

    def test_decrement_performers(self) -> None:
        """Test decrement_performers method."""
        task = Task(
            creator_id="user-123",
            title="Test",
            description="Test description",
            instructions="Test instructions",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("1.00"),
            service_fee=Decimal("0.15"),
            total_cost=Decimal("1.15"),
            max_performers=10,
            current_performers=5,
        )

        task.decrement_performers()
        assert task.current_performers == 4

        # Test zero limit
        task.current_performers = 0
        with pytest.raises(ValueError, match="Current performers already at zero"):
            task.decrement_performers()

    def test_task_repr(self) -> None:
        """Test task string representation."""
        task = Task(
            id="task-123",
            creator_id="user-123",
            title="Like my Instagram post",
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

        repr_str = repr(task)
        assert "Task" in repr_str
        assert "task-123" in repr_str
        assert "active" in repr_str
        assert "instagram" in repr_str


class TestTaskAssignmentModel:
    """Tests for TaskAssignment model."""

    def test_create_assignment(self) -> None:
        """Test creating a task assignment."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.ASSIGNED,
        )

        assert assignment.task_id == "task-123"
        assert assignment.performer_id == "user-456"
        assert assignment.status == AssignmentStatusEnum.ASSIGNED

    def test_mark_started(self) -> None:
        """Test marking assignment as started."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.ASSIGNED,
        )

        assignment.mark_started()
        assert assignment.status == AssignmentStatusEnum.STARTED
        assert assignment.started_at is not None

        # Test invalid status transition
        with pytest.raises(ValueError):
            assignment.mark_started()

    def test_submit_proof(self) -> None:
        """Test submitting proof."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.STARTED,
        )

        assignment.submit_proof()
        assert assignment.status == AssignmentStatusEnum.PROOF_SUBMITTED
        assert assignment.proof_submitted_at is not None

    def test_approve_assignment(self) -> None:
        """Test approving assignment."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.PROOF_SUBMITTED,
        )

        assignment.approve(rating=5, review="Great job!")
        assert assignment.status == AssignmentStatusEnum.APPROVED
        assert assignment.rating == 5
        assert assignment.review == "Great job!"
        assert assignment.completed_at is not None
        assert assignment.verified_at is not None

    def test_approve_invalid_rating(self) -> None:
        """Test approving with invalid rating."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.PROOF_SUBMITTED,
        )

        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            assignment.approve(rating=6)

        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            assignment.approve(rating=0)

    def test_reject_assignment(self) -> None:
        """Test rejecting assignment."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.PROOF_SUBMITTED,
        )

        assignment.reject(review="Does not meet requirements")
        assert assignment.status == AssignmentStatusEnum.REJECTED
        assert assignment.review == "Does not meet requirements"
        assert assignment.verified_at is not None

    def test_cancel_assignment(self) -> None:
        """Test cancelling assignment."""
        assignment = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.ASSIGNED,
        )

        assignment.cancel()
        assert assignment.status == AssignmentStatusEnum.CANCELLED

        # Test cannot cancel from terminal status
        assignment2 = TaskAssignment(
            task_id="task-123",
            performer_id="user-456",
            status=AssignmentStatusEnum.APPROVED,
        )

        with pytest.raises(ValueError, match="Cannot cancel assignment from terminal status"):
            assignment2.cancel()


class TestTaskHistoryModel:
    """Tests for TaskHistory model."""

    def test_create_entry(self) -> None:
        """Test creating history entry."""
        history = TaskHistory.create_entry(
            task_id="task-123",
            previous_status="draft",
            new_status="active",
            changed_by="user-456",
            reason="Task published",
            metadata={"ip_address": "192.168.1.1"},
        )

        assert history.task_id == "task-123"
        assert history.previous_status == "draft"
        assert history.new_status == "active"
        assert history.changed_by == "user-456"
        assert history.reason == "Task published"
        assert history.metadata == {"ip_address": "192.168.1.1"}
        assert history.id is not None
        assert history.created_at is not None

    def test_history_to_dict(self) -> None:
        """Test converting history to dictionary."""
        history = TaskHistory.create_entry(
            task_id="task-123",
            previous_status="draft",
            new_status="active",
            changed_by="user-456",
        )

        history_dict = history.to_dict()

        assert history_dict["task_id"] == "task-123"
        assert history_dict["previous_status"] == "draft"
        assert history_dict["new_status"] == "active"
        assert history_dict["changed_by"] == "user-456"
        assert "created_at" in history_dict

    def test_history_repr(self) -> None:
        """Test history string representation."""
        history = TaskHistory.create_entry(
            task_id="task-123",
            previous_status="draft",
            new_status="active",
            changed_by="user-456",
        )

        repr_str = repr(history)
        assert "TaskHistory" in repr_str
        assert "task-123" in repr_str
        assert "draft" in repr_str
        assert "active" in repr_str
