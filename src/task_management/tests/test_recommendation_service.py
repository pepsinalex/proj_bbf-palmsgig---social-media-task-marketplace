"""
Tests for RecommendationService.

Comprehensive tests for task recommendation service including user preference
calculation, task scoring, and personalized recommendation generation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import AssignmentStatusEnum, TaskAssignment
from src.task_management.schemas.discovery import RecommendationResponse, TaskDiscoveryResponse
from src.task_management.services.recommendation_service import RecommendationService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def recommendation_service(mock_session: AsyncMock) -> RecommendationService:
    """Create RecommendationService instance with mock session."""
    return RecommendationService(mock_session)


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-123",
        creator_id="creator-456",
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
def sample_active_tasks() -> list[Task]:
    """Create multiple active tasks for recommendation testing."""
    now = datetime.utcnow()
    return [
        Task(
            id=f"task-{i}",
            creator_id="creator-999",
            title=f"Task {i}",
            description=f"Description {i}",
            instructions=f"Instructions {i}",
            platform=PlatformEnum.INSTAGRAM if i % 2 == 0 else PlatformEnum.FACEBOOK,
            task_type=TaskTypeEnum.LIKE if i % 2 == 0 else TaskTypeEnum.FOLLOW,
            budget=Decimal(f"{i + 5}.00"),
            service_fee=Decimal(f"{(i + 5) * 0.15:.2f}"),
            total_cost=Decimal(f"{(i + 5) * 1.15:.2f}"),
            max_performers=100,
            current_performers=i * 5,
            status=TaskStatusEnum.ACTIVE,
            target_criteria={},
            expires_at=now + timedelta(days=7),
            created_at=now - timedelta(hours=i),
            updated_at=now,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_assignments() -> list[tuple[Task, TaskAssignment]]:
    """Create sample assignment history for testing."""
    now = datetime.utcnow()
    assignments = []

    for i in range(5):
        task = Task(
            id=f"past-task-{i}",
            creator_id=f"creator-{i}",
            title=f"Past Task {i}",
            description=f"Description {i}",
            instructions=f"Instructions {i}",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal(f"{i + 2}.00"),
            service_fee=Decimal(f"{(i + 2) * 0.15:.2f}"),
            total_cost=Decimal(f"{(i + 2) * 1.15:.2f}"),
            max_performers=50,
            current_performers=50,
            status=TaskStatusEnum.COMPLETED,
            target_criteria={},
            expires_at=None,
            created_at=now - timedelta(days=i * 10),
            updated_at=now - timedelta(days=i * 10),
        )

        assignment = TaskAssignment(
            id=f"assignment-{i}",
            task_id=task.id,
            user_id="user-123",
            status=AssignmentStatusEnum.APPROVED,
            proof_url=f"https://example.com/proof-{i}",
            rating=5 if i % 2 == 0 else 4,
            created_at=now - timedelta(days=i * 10),
            updated_at=now - timedelta(days=i * 10),
        )

        assignments.append((task, assignment))

    return assignments


class TestRecommendationServiceInitialization:
    """Tests for RecommendationService initialization."""

    def test_initialization_success(self, mock_session: AsyncMock) -> None:
        """Test successful RecommendationService initialization."""
        service = RecommendationService(mock_session)

        assert service.db_session == mock_session


class TestGenerateRecommendations:
    """Tests for generate_recommendations method."""

    async def test_generate_recommendations_success(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_active_tasks: list[Task],
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test successful recommendation generation."""
        user_id = "user-123"

        # Mock assignment history query
        history_result = MagicMock()
        history_result.all.return_value = sample_assignments

        # Mock active tasks query
        tasks_result = MagicMock()
        tasks_result.scalars.return_value.all.return_value = sample_active_tasks

        mock_session.execute.side_effect = [history_result, tasks_result]

        recommendations = await recommendation_service.generate_recommendations(
            user_id=user_id, limit=3, min_score=0.3
        )

        assert len(recommendations) <= 3
        assert all(isinstance(r, RecommendationResponse) for r in recommendations)
        assert all(0 <= r.match_score <= 1 for r in recommendations)
        assert all(r.recommendation_reason for r in recommendations)

    async def test_generate_recommendations_sorted_by_score(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_active_tasks: list[Task],
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test recommendations are sorted by match score."""
        user_id = "user-123"

        history_result = MagicMock()
        history_result.all.return_value = sample_assignments

        tasks_result = MagicMock()
        tasks_result.scalars.return_value.all.return_value = sample_active_tasks

        mock_session.execute.side_effect = [history_result, tasks_result]

        recommendations = await recommendation_service.generate_recommendations(
            user_id=user_id, limit=5, min_score=0.0
        )

        # Verify sorted descending by match_score
        scores = [r.match_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)

    async def test_generate_recommendations_respects_min_score(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_active_tasks: list[Task],
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test recommendations respect minimum score threshold."""
        user_id = "user-123"

        history_result = MagicMock()
        history_result.all.return_value = sample_assignments

        tasks_result = MagicMock()
        tasks_result.scalars.return_value.all.return_value = sample_active_tasks

        mock_session.execute.side_effect = [history_result, tasks_result]

        recommendations = await recommendation_service.generate_recommendations(
            user_id=user_id, limit=10, min_score=0.8
        )

        # All recommendations should meet min_score
        assert all(r.match_score >= 0.8 for r in recommendations)

    async def test_generate_recommendations_no_candidates(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test recommendations with no candidate tasks."""
        user_id = "user-123"

        history_result = MagicMock()
        history_result.all.return_value = sample_assignments

        tasks_result = MagicMock()
        tasks_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [history_result, tasks_result]

        recommendations = await recommendation_service.generate_recommendations(
            user_id=user_id, limit=10, min_score=0.5
        )

        assert len(recommendations) == 0

    async def test_generate_recommendations_handles_error(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
    ) -> None:
        """Test generate_recommendations handles errors."""
        user_id = "user-123"

        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await recommendation_service.generate_recommendations(user_id=user_id)


class TestCalculateUserPreferences:
    """Tests for calculate_user_preferences method."""

    async def test_calculate_user_preferences_with_history(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test preference calculation with assignment history."""
        user_id = "user-123"

        result = MagicMock()
        result.all.return_value = sample_assignments

        mock_session.execute.return_value = result

        preferences = await recommendation_service.calculate_user_preferences(user_id)

        assert "platform_affinity" in preferences
        assert "task_type_affinity" in preferences
        assert "budget_range" in preferences
        assert "total_assignments" in preferences
        assert "success_rate" in preferences

        assert preferences["total_assignments"] == len(sample_assignments)
        assert isinstance(preferences["platform_affinity"], dict)
        assert isinstance(preferences["task_type_affinity"], dict)

    async def test_calculate_user_preferences_no_history(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
    ) -> None:
        """Test preference calculation with no history returns defaults."""
        user_id = "new-user"

        result = MagicMock()
        result.all.return_value = []

        mock_session.execute.return_value = result

        preferences = await recommendation_service.calculate_user_preferences(user_id)

        assert preferences["total_assignments"] == 0
        assert preferences["success_rate"] == 0.0
        assert "instagram" in preferences["platform_affinity"]
        assert "like" in preferences["task_type_affinity"]

    async def test_calculate_user_preferences_platform_affinity(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test platform affinity calculation."""
        user_id = "user-123"

        result = MagicMock()
        result.all.return_value = sample_assignments

        mock_session.execute.return_value = result

        preferences = await recommendation_service.calculate_user_preferences(user_id)

        platform_affinity = preferences["platform_affinity"]

        # All sample assignments are Instagram
        assert "instagram" in platform_affinity
        assert platform_affinity["instagram"] > 0

    async def test_calculate_user_preferences_budget_range(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test budget range calculation."""
        user_id = "user-123"

        result = MagicMock()
        result.all.return_value = sample_assignments

        mock_session.execute.return_value = result

        preferences = await recommendation_service.calculate_user_preferences(user_id)

        budget_range = preferences["budget_range"]

        assert "min" in budget_range
        assert "max" in budget_range
        assert "avg" in budget_range
        assert budget_range["min"] <= budget_range["avg"] <= budget_range["max"]

    async def test_calculate_user_preferences_handles_error(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
    ) -> None:
        """Test preference calculation handles errors and returns defaults."""
        user_id = "user-123"

        mock_session.execute.side_effect = Exception("Database error")

        preferences = await recommendation_service.calculate_user_preferences(user_id)

        # Should return default preferences on error
        assert preferences["total_assignments"] == 0
        assert "platform_affinity" in preferences


class TestScoreTaskRelevance:
    """Tests for score_task_relevance method."""

    async def test_score_task_relevance_high_match(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test task scoring with high match preferences."""
        user_id = "user-123"
        preferences = {
            "platform_affinity": {"instagram": 0.9},
            "task_type_affinity": {"like": 0.85},
            "budget_range": {"min": 8.0, "max": 12.0, "avg": 10.0},
            "total_assignments": 10,
            "success_rate": 0.9,
        }

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        assert 0 <= score <= 1
        assert "platform_affinity" in factors
        assert "task_type_preference" in factors
        assert "budget_compatibility" in factors
        assert "availability" in factors
        assert "freshness" in factors
        assert factors["platform_affinity"] == 0.9

    async def test_score_task_relevance_low_match(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test task scoring with low match preferences."""
        user_id = "user-123"
        preferences = {
            "platform_affinity": {"facebook": 0.9, "instagram": 0.2},
            "task_type_affinity": {"follow": 0.8, "like": 0.1},
            "budget_range": {"min": 0.5, "max": 3.0, "avg": 1.5},
            "total_assignments": 5,
            "success_rate": 0.5,
        }

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        assert 0 <= score <= 1
        assert factors["platform_affinity"] == 0.2
        assert factors["task_type_preference"] == 0.1

    async def test_score_task_relevance_default_preferences(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test task scoring with default preferences."""
        user_id = "new-user"
        preferences = recommendation_service._get_default_preferences()

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        assert 0 <= score <= 1
        assert "platform_affinity" in factors
        assert "task_type_preference" in factors

    async def test_score_task_relevance_budget_within_range(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test budget scoring when task is within user's range."""
        user_id = "user-123"
        preferences = {
            "platform_affinity": {},
            "task_type_affinity": {},
            "budget_range": {"min": 5.0, "max": 15.0, "avg": 10.0},
        }

        sample_task.budget = Decimal("10.00")

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        budget_score = factors["budget_compatibility"]
        assert budget_score >= 0.5

    async def test_score_task_relevance_budget_below_range(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test budget scoring when task is below user's range."""
        user_id = "user-123"
        preferences = {
            "platform_affinity": {},
            "task_type_affinity": {},
            "budget_range": {"min": 15.0, "max": 25.0, "avg": 20.0},
        }

        sample_task.budget = Decimal("10.00")

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        budget_score = factors["budget_compatibility"]
        assert budget_score == 0.7

    async def test_score_task_relevance_budget_above_range(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test budget scoring when task is above user's range."""
        user_id = "user-123"
        preferences = {
            "platform_affinity": {},
            "task_type_affinity": {},
            "budget_range": {"min": 1.0, "max": 5.0, "avg": 3.0},
        }

        sample_task.budget = Decimal("10.00")

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        budget_score = factors["budget_compatibility"]
        assert budget_score == 0.6

    async def test_score_task_relevance_availability_score(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test availability scoring based on slots."""
        user_id = "user-123"
        preferences = recommendation_service._get_default_preferences()

        sample_task.max_performers = 100
        sample_task.current_performers = 10

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        availability_score = factors["availability"]
        assert availability_score > 0.8

    async def test_score_task_relevance_freshness_score(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test freshness scoring for recent tasks."""
        user_id = "user-123"
        preferences = recommendation_service._get_default_preferences()

        sample_task.created_at = datetime.utcnow() - timedelta(hours=1)

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        freshness_score = factors["freshness"]
        assert freshness_score > 0.9

    async def test_score_task_relevance_handles_error(
        self,
        recommendation_service: RecommendationService,
        sample_task: Task,
    ) -> None:
        """Test score_task_relevance handles errors gracefully."""
        user_id = "user-123"
        preferences = None

        score, factors = await recommendation_service.score_task_relevance(
            sample_task, user_id, preferences
        )

        assert score == 0.5
        assert "error" in factors


class TestGetUserPerformanceHistory:
    """Tests for get_user_performance_history method."""

    async def test_get_user_performance_history_success(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test successful performance history retrieval."""
        user_id = "user-123"

        result = MagicMock()
        result.all.return_value = sample_assignments

        mock_session.execute.return_value = result

        history = await recommendation_service.get_user_performance_history(user_id)

        assert len(history) == len(sample_assignments)
        assert all(isinstance(record, dict) for record in history)
        assert all("task_id" in record for record in history)
        assert all("platform" in record for record in history)
        assert all("status" in record for record in history)

    async def test_get_user_performance_history_empty(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
    ) -> None:
        """Test performance history with no records."""
        user_id = "new-user"

        result = MagicMock()
        result.all.return_value = []

        mock_session.execute.return_value = result

        history = await recommendation_service.get_user_performance_history(user_id)

        assert len(history) == 0

    async def test_get_user_performance_history_respects_limit(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
        sample_assignments: list[tuple[Task, TaskAssignment]],
    ) -> None:
        """Test performance history respects limit parameter."""
        user_id = "user-123"

        result = MagicMock()
        result.all.return_value = sample_assignments[:3]

        mock_session.execute.return_value = result

        history = await recommendation_service.get_user_performance_history(
            user_id, limit=3
        )

        assert len(history) <= 3

    async def test_get_user_performance_history_handles_error(
        self,
        recommendation_service: RecommendationService,
        mock_session: AsyncMock,
    ) -> None:
        """Test performance history handles errors."""
        user_id = "user-123"

        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await recommendation_service.get_user_performance_history(user_id)


class TestGetDefaultPreferences:
    """Tests for _get_default_preferences method."""

    def test_get_default_preferences_structure(
        self, recommendation_service: RecommendationService
    ) -> None:
        """Test default preferences have correct structure."""
        preferences = recommendation_service._get_default_preferences()

        assert "platform_affinity" in preferences
        assert "task_type_affinity" in preferences
        assert "budget_range" in preferences
        assert "total_assignments" in preferences
        assert "success_rate" in preferences

    def test_get_default_preferences_platforms(
        self, recommendation_service: RecommendationService
    ) -> None:
        """Test default preferences include all platforms."""
        preferences = recommendation_service._get_default_preferences()

        platform_affinity = preferences["platform_affinity"]

        assert "instagram" in platform_affinity
        assert "facebook" in platform_affinity
        assert "twitter" in platform_affinity
        assert "youtube" in platform_affinity
        assert "tiktok" in platform_affinity
        assert "linkedin" in platform_affinity

    def test_get_default_preferences_task_types(
        self, recommendation_service: RecommendationService
    ) -> None:
        """Test default preferences include all task types."""
        preferences = recommendation_service._get_default_preferences()

        task_type_affinity = preferences["task_type_affinity"]

        assert "like" in task_type_affinity
        assert "follow" in task_type_affinity
        assert "share" in task_type_affinity
        assert "comment" in task_type_affinity
        assert "view" in task_type_affinity
        assert "subscribe" in task_type_affinity
        assert "engagement" in task_type_affinity

    def test_get_default_preferences_values(
        self, recommendation_service: RecommendationService
    ) -> None:
        """Test default preferences have reasonable values."""
        preferences = recommendation_service._get_default_preferences()

        assert preferences["total_assignments"] == 0
        assert preferences["success_rate"] == 0.0
        assert preferences["budget_range"]["min"] > 0
        assert preferences["budget_range"]["max"] > preferences["budget_range"]["min"]


class TestGenerateRecommendationReason:
    """Tests for _generate_recommendation_reason method."""

    def test_generate_recommendation_reason_high_platform_score(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation with high platform score."""
        factors = {
            "platform_affinity": 0.85,
            "task_type_preference": 0.4,
            "budget_compatibility": 0.5,
            "availability": 0.6,
            "freshness": 0.7,
        }

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert "Instagram" in reason or "experience" in reason

    def test_generate_recommendation_reason_high_task_type_score(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation with high task type score."""
        factors = {
            "platform_affinity": 0.4,
            "task_type_preference": 0.75,
            "budget_compatibility": 0.5,
            "availability": 0.6,
            "freshness": 0.7,
        }

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert "similar" in reason or "like" in reason

    def test_generate_recommendation_reason_high_budget_score(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation with high budget score."""
        factors = {
            "platform_affinity": 0.4,
            "task_type_preference": 0.4,
            "budget_compatibility": 0.85,
            "availability": 0.6,
            "freshness": 0.7,
        }

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert "Budget" in reason or "$" in reason

    def test_generate_recommendation_reason_high_availability(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation with high availability."""
        factors = {
            "platform_affinity": 0.4,
            "task_type_preference": 0.4,
            "budget_compatibility": 0.5,
            "availability": 0.9,
            "freshness": 0.7,
        }

        sample_task.current_performers = 10
        sample_task.max_performers = 100

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert "spots" in reason or "available" in reason

    def test_generate_recommendation_reason_multiple_factors(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation combines multiple high factors."""
        factors = {
            "platform_affinity": 0.85,
            "task_type_preference": 0.75,
            "budget_compatibility": 0.8,
            "availability": 0.9,
            "freshness": 0.9,
        }

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert ";" in reason  # Multiple reasons joined with semicolon

    def test_generate_recommendation_reason_low_scores(
        self, recommendation_service: RecommendationService, sample_task: Task
    ) -> None:
        """Test reason generation with low scores provides fallback."""
        factors = {
            "platform_affinity": 0.3,
            "task_type_preference": 0.3,
            "budget_compatibility": 0.4,
            "availability": 0.5,
            "freshness": 0.4,
        }

        reason = recommendation_service._generate_recommendation_reason(
            sample_task, factors
        )

        assert "Popular" in reason or "task" in reason
