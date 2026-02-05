"""
Task Recommendation Service with User Preference Analysis.

Provides intelligent task recommendations based on user performance history,
platform affinity, task type preferences, and budget compatibility.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.task_management.enums.task_enums import PlatformEnum, TaskStatusEnum, TaskTypeEnum
from src.task_management.models.task import Task
from src.task_management.models.task_assignment import AssignmentStatusEnum, TaskAssignment
from src.task_management.schemas.discovery import RecommendationResponse, TaskDiscoveryResponse

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for generating personalized task recommendations.

    Analyzes user behavior and performance to suggest relevant tasks
    with scored recommendations and detailed reasoning.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize RecommendationService with database session.

        Args:
            db_session: Active async database session
        """
        self.db_session = db_session
        logger.info("RecommendationService initialized")

    async def generate_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[RecommendationResponse]:
        """
        Generate personalized task recommendations for a user.

        Args:
            user_id: ID of the user to generate recommendations for
            limit: Maximum number of recommendations to return
            min_score: Minimum match score threshold (0-1)

        Returns:
            List of recommendation responses with scored tasks

        Raises:
            Exception: If recommendation generation fails
        """
        try:
            logger.info(
                "Generating recommendations",
                extra={
                    "user_id": user_id,
                    "limit": limit,
                    "min_score": min_score,
                },
            )

            # Calculate user preferences based on history
            preferences = await self.calculate_user_preferences(user_id)

            logger.debug(
                "User preferences calculated",
                extra={"user_id": user_id, "preferences": preferences},
            )

            # Get active tasks excluding user's own tasks
            query = (
                select(Task)
                .where(
                    Task.status == TaskStatusEnum.ACTIVE,
                    Task.creator_id != user_id,
                    Task.expires_at > datetime.utcnow(),
                    Task.current_performers < Task.max_performers,
                )
                .order_by(Task.created_at.desc())
                .limit(limit * 3)
            )

            result = await self.db_session.execute(query)
            candidate_tasks = result.scalars().all()

            logger.debug(
                "Candidate tasks retrieved",
                extra={"user_id": user_id, "candidate_count": len(candidate_tasks)},
            )

            # Score and rank tasks
            recommendations = []
            for task in candidate_tasks:
                match_score, factors = await self.score_task_relevance(
                    task, user_id, preferences
                )

                if match_score >= min_score:
                    reason = self._generate_recommendation_reason(task, factors)

                    task_response = TaskDiscoveryResponse(
                        id=task.id,
                        title=task.title,
                        description=task.description,
                        instructions=task.instructions,
                        platform=task.platform,
                        task_type=task.task_type,
                        budget=task.budget,
                        service_fee=task.service_fee,
                        total_cost=task.total_cost,
                        max_performers=task.max_performers,
                        current_performers=task.current_performers,
                        status=task.status,
                        creator_id=task.creator_id,
                        target_criteria=task.target_criteria,
                        expires_at=task.expires_at,
                        created_at=task.created_at,
                        updated_at=task.updated_at,
                    )

                    recommendation = RecommendationResponse(
                        task=task_response,
                        match_score=match_score,
                        recommendation_reason=reason,
                        factors=factors,
                    )

                    recommendations.append(recommendation)

            # Sort by match score descending
            recommendations.sort(key=lambda r: r.match_score, reverse=True)

            # Limit to requested number
            recommendations = recommendations[:limit]

            logger.info(
                "Recommendations generated successfully",
                extra={
                    "user_id": user_id,
                    "recommendation_count": len(recommendations),
                    "avg_score": (
                        sum(r.match_score for r in recommendations) / len(recommendations)
                        if recommendations
                        else 0
                    ),
                },
            )

            return recommendations

        except Exception as e:
            logger.error(
                "Failed to generate recommendations",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def calculate_user_preferences(self, user_id: str) -> dict[str, Any]:
        """
        Calculate user preferences from performance history.

        Analyzes completed assignments to determine platform affinity,
        task type preferences, and budget range.

        Args:
            user_id: User ID to analyze

        Returns:
            Dictionary containing preference metrics

        Raises:
            Exception: If preference calculation fails
        """
        try:
            # Get user's performance history (last 90 days)
            history_start = datetime.utcnow() - timedelta(days=90)

            query = (
                select(Task, TaskAssignment)
                .join(TaskAssignment, Task.id == TaskAssignment.task_id)
                .where(
                    TaskAssignment.user_id == user_id,
                    TaskAssignment.created_at >= history_start,
                )
            )

            result = await self.db_session.execute(query)
            assignments = result.all()

            if not assignments:
                logger.info(
                    "No assignment history found for user",
                    extra={"user_id": user_id},
                )
                return self._get_default_preferences()

            # Calculate platform affinity
            platform_counts = defaultdict(int)
            platform_success = defaultdict(int)

            # Calculate task type preferences
            task_type_counts = defaultdict(int)
            task_type_success = defaultdict(int)

            # Track budget ranges
            budgets = []

            for task, assignment in assignments:
                platform_counts[task.platform.value] += 1
                task_type_counts[task.task_type.value] += 1
                budgets.append(float(task.budget))

                # Track successful completions
                if assignment.status == AssignmentStatusEnum.APPROVED:
                    platform_success[task.platform.value] += 1
                    task_type_success[task.task_type.value] += 1

            # Calculate affinity scores (frequency * success rate)
            total_tasks = len(assignments)

            platform_affinity = {}
            for platform, count in platform_counts.items():
                frequency = count / total_tasks
                success_rate = (
                    platform_success[platform] / count if count > 0 else 0
                )
                platform_affinity[platform] = frequency * (0.5 + 0.5 * success_rate)

            task_type_affinity = {}
            for task_type, count in task_type_counts.items():
                frequency = count / total_tasks
                success_rate = (
                    task_type_success[task_type] / count if count > 0 else 0
                )
                task_type_affinity[task_type] = frequency * (
                    0.5 + 0.5 * success_rate
                )

            # Calculate budget preferences
            avg_budget = sum(budgets) / len(budgets) if budgets else 0
            min_budget = min(budgets) if budgets else 0
            max_budget = max(budgets) if budgets else 0

            preferences = {
                "platform_affinity": platform_affinity,
                "task_type_affinity": task_type_affinity,
                "budget_range": {
                    "min": min_budget,
                    "max": max_budget,
                    "avg": avg_budget,
                },
                "total_assignments": total_tasks,
                "success_rate": (
                    sum(platform_success.values()) / total_tasks
                    if total_tasks > 0
                    else 0
                ),
            }

            logger.debug(
                "User preferences calculated",
                extra={"user_id": user_id, "preferences": preferences},
            )

            return preferences

        except Exception as e:
            logger.error(
                "Failed to calculate user preferences",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return self._get_default_preferences()

    async def score_task_relevance(
        self, task: Task, user_id: str, preferences: dict[str, Any]
    ) -> tuple[float, dict[str, Any]]:
        """
        Score task relevance for a user based on preferences.

        Args:
            task: Task to score
            user_id: User ID for scoring context
            preferences: User preference dictionary

        Returns:
            Tuple of (match_score, factors_dict)

        Raises:
            Exception: If scoring fails
        """
        try:
            factors = {}

            # Platform affinity score (weight: 0.35)
            platform_affinity = preferences.get("platform_affinity", {})
            platform_score = platform_affinity.get(task.platform.value, 0.3)
            factors["platform_affinity"] = platform_score

            # Task type preference score (weight: 0.30)
            task_type_affinity = preferences.get("task_type_affinity", {})
            task_type_score = task_type_affinity.get(task.task_type.value, 0.3)
            factors["task_type_preference"] = task_type_score

            # Budget compatibility score (weight: 0.20)
            budget_range = preferences.get(
                "budget_range", {"min": 0, "max": 100, "avg": 1}
            )
            task_budget = float(task.budget)

            if task_budget < budget_range["min"]:
                budget_score = 0.7
            elif task_budget > budget_range["max"]:
                budget_score = 0.6
            else:
                # Within range, score based on distance from average
                avg_budget = budget_range["avg"]
                if avg_budget > 0:
                    distance_from_avg = abs(task_budget - avg_budget) / avg_budget
                    budget_score = max(0.5, 1.0 - distance_from_avg)
                else:
                    budget_score = 0.7

            factors["budget_compatibility"] = budget_score

            # Availability score (weight: 0.10)
            available_slots = task.max_performers - task.current_performers
            availability_ratio = available_slots / task.max_performers
            availability_score = 0.5 + 0.5 * availability_ratio
            factors["availability"] = availability_score

            # Freshness score (weight: 0.05)
            task_age_hours = (datetime.utcnow() - task.created_at).total_seconds() / 3600
            freshness_score = max(0.3, 1.0 - (task_age_hours / 168))
            factors["freshness"] = freshness_score

            # Calculate weighted total score
            total_score = (
                platform_score * 0.35
                + task_type_score * 0.30
                + budget_score * 0.20
                + availability_score * 0.10
                + freshness_score * 0.05
            )

            # Normalize to 0-1 range
            total_score = max(0.0, min(1.0, total_score))
            factors["total_score"] = total_score

            logger.debug(
                "Task relevance scored",
                extra={
                    "task_id": task.id,
                    "user_id": user_id,
                    "score": total_score,
                    "factors": factors,
                },
            )

            return total_score, factors

        except Exception as e:
            logger.error(
                "Failed to score task relevance",
                extra={
                    "task_id": task.id,
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0.5, {"error": "scoring_failed"}

    async def get_user_performance_history(
        self, user_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get user's performance history with assignment details.

        Args:
            user_id: User ID to retrieve history for
            limit: Maximum number of records to return

        Returns:
            List of assignment history records

        Raises:
            Exception: If history retrieval fails
        """
        try:
            query = (
                select(Task, TaskAssignment)
                .join(TaskAssignment, Task.id == TaskAssignment.task_id)
                .where(TaskAssignment.user_id == user_id)
                .order_by(TaskAssignment.created_at.desc())
                .limit(limit)
            )

            result = await self.db_session.execute(query)
            assignments = result.all()

            history = []
            for task, assignment in assignments:
                record = {
                    "task_id": task.id,
                    "task_title": task.title,
                    "platform": task.platform.value,
                    "task_type": task.task_type.value,
                    "budget": float(task.budget),
                    "status": assignment.status.value,
                    "assigned_at": assignment.created_at.isoformat(),
                    "completed_at": (
                        assignment.updated_at.isoformat()
                        if assignment.status == AssignmentStatusEnum.APPROVED
                        else None
                    ),
                    "rating": assignment.rating,
                }
                history.append(record)

            logger.info(
                "User performance history retrieved",
                extra={"user_id": user_id, "record_count": len(history)},
            )

            return history

        except Exception as e:
            logger.error(
                "Failed to retrieve user performance history",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _get_default_preferences(self) -> dict[str, Any]:
        """
        Get default preferences for users with no history.

        Returns:
            Default preference dictionary
        """
        return {
            "platform_affinity": {
                "instagram": 0.4,
                "facebook": 0.3,
                "twitter": 0.3,
                "youtube": 0.3,
                "tiktok": 0.3,
                "linkedin": 0.2,
            },
            "task_type_affinity": {
                "like": 0.5,
                "follow": 0.4,
                "share": 0.4,
                "comment": 0.3,
                "view": 0.4,
                "subscribe": 0.3,
                "engagement": 0.3,
            },
            "budget_range": {"min": 0.5, "max": 10.0, "avg": 2.0},
            "total_assignments": 0,
            "success_rate": 0.0,
        }

    def _generate_recommendation_reason(
        self, task: Task, factors: dict[str, Any]
    ) -> str:
        """
        Generate human-readable recommendation reason.

        Args:
            task: Task being recommended
            factors: Scoring factors

        Returns:
            Descriptive recommendation reason string
        """
        reasons = []

        platform_score = factors.get("platform_affinity", 0)
        if platform_score > 0.6:
            reasons.append(
                f"Strong match for your {task.platform.value.title()} experience"
            )

        task_type_score = factors.get("task_type_preference", 0)
        if task_type_score > 0.6:
            reasons.append(
                f"You've successfully completed similar {task.task_type.value} tasks"
            )

        budget_score = factors.get("budget_compatibility", 0)
        if budget_score > 0.7:
            reasons.append(f"Budget (${task.budget}) matches your preferences")

        availability_score = factors.get("availability", 0)
        if availability_score > 0.8:
            available_slots = task.max_performers - task.current_performers
            reasons.append(f"{available_slots} spots still available")

        if not reasons:
            reasons.append(
                f"Popular {task.task_type.value} task on {task.platform.value.title()}"
            )

        return "; ".join(reasons)
