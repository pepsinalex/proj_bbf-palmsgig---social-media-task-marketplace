"""
Unit tests for ValidationService.

Tests all validation logic including draft validation, publish validation,
and platform-specific rules.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from src.task_management.enums.task_enums import (
    PlatformEnum,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.models.task import Task
from src.task_management.services.validation_service import ValidationService


class TestValidationService:
    """Test suite for ValidationService."""

    def test_validate_draft_valid_minimal(self) -> None:
        """Test validating a minimal valid draft."""
        draft_data = {"title": "My Task"}
        errors = ValidationService.validate_draft(draft_data)

        assert errors == []

    def test_validate_draft_valid_complete(self) -> None:
        """Test validating a complete valid draft."""
        draft_data = {
            "title": "Like my Instagram post",
            "platform": PlatformEnum.INSTAGRAM,
            "task_type": TaskTypeEnum.LIKE,
            "budget": Decimal("10.00"),
            "max_performers": 100,
        }
        errors = ValidationService.validate_draft(draft_data)

        assert errors == []

    def test_validate_draft_missing_title(self) -> None:
        """Test validating draft without title."""
        draft_data = {}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Title is required" in error for error in errors)

    def test_validate_draft_empty_title(self) -> None:
        """Test validating draft with empty title."""
        draft_data = {"title": ""}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Title is required" in error for error in errors)

    def test_validate_draft_short_title(self) -> None:
        """Test validating draft with short title."""
        draft_data = {"title": "Ab"}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("at least 3 characters" in error for error in errors)

    def test_validate_draft_long_title(self) -> None:
        """Test validating draft with long title."""
        draft_data = {"title": "A" * 256}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("255 characters" in error for error in errors)

    def test_validate_draft_invalid_platform_task_type(self) -> None:
        """Test validating draft with incompatible platform-task type."""
        draft_data = {
            "title": "Subscribe to my channel",
            "platform": PlatformEnum.FACEBOOK,
            "task_type": TaskTypeEnum.SUBSCRIBE,
        }
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("not compatible" in error for error in errors)

    def test_validate_draft_valid_platform_task_type(self) -> None:
        """Test validating draft with compatible platform-task type."""
        draft_data = {
            "title": "Subscribe to my YouTube channel",
            "platform": PlatformEnum.YOUTUBE,
            "task_type": TaskTypeEnum.SUBSCRIBE,
        }
        errors = ValidationService.validate_draft(draft_data)

        assert errors == []

    def test_validate_draft_negative_budget(self) -> None:
        """Test validating draft with negative budget."""
        draft_data = {"title": "My Task", "budget": Decimal("-10.00")}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Budget must be positive" in error for error in errors)

    def test_validate_draft_zero_budget(self) -> None:
        """Test validating draft with zero budget."""
        draft_data = {"title": "My Task", "budget": Decimal("0.00")}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Budget must be positive" in error for error in errors)

    def test_validate_draft_negative_max_performers(self) -> None:
        """Test validating draft with negative max_performers."""
        draft_data = {"title": "My Task", "max_performers": -10}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Max performers must be positive" in error for error in errors)

    def test_validate_draft_zero_max_performers(self) -> None:
        """Test validating draft with zero max_performers."""
        draft_data = {"title": "My Task", "max_performers": 0}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("Max performers must be positive" in error for error in errors)

    def test_validate_draft_excessive_max_performers(self) -> None:
        """Test validating draft with excessive max_performers."""
        draft_data = {"title": "My Task", "max_performers": 10001}
        errors = ValidationService.validate_draft(draft_data)

        assert len(errors) > 0
        assert any("10,000" in error for error in errors)

    def test_validate_for_publish_valid_task(self) -> None:
        """Test validating a complete valid task for publishing."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert errors == []

    def test_validate_for_publish_missing_title(self) -> None:
        """Test validating task without title."""
        task = Task(
            creator_id="user-123",
            title="",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Title is required" in error for error in errors)

    def test_validate_for_publish_missing_description(self) -> None:
        """Test validating task without description."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Description is required" in error for error in errors)

    def test_validate_for_publish_missing_instructions(self) -> None:
        """Test validating task without instructions."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Instructions are required" in error for error in errors)

    def test_validate_for_publish_missing_platform(self) -> None:
        """Test validating task without platform."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=None,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Platform is required" in error for error in errors)

    def test_validate_for_publish_missing_task_type(self) -> None:
        """Test validating task without task_type."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=None,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Task type is required" in error for error in errors)

    def test_validate_for_publish_zero_budget(self) -> None:
        """Test validating task with zero budget."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("0.00"),
            service_fee=Decimal("0.00"),
            total_cost=Decimal("0.00"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Budget is required and must be positive" in error for error in errors)

    def test_validate_for_publish_zero_max_performers(self) -> None:
        """Test validating task with zero max_performers."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like 3. Screenshot",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=0,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("Max performers is required and must be positive" in error for error in errors)

    def test_validate_for_publish_incompatible_platform_task_type(self) -> None:
        """Test validating task with incompatible platform-task type."""
        task = Task(
            creator_id="user-123",
            title="Subscribe to me",
            description="Please subscribe to my Facebook page",
            instructions="1. Visit URL 2. Click subscribe",
            platform=PlatformEnum.FACEBOOK,
            task_type=TaskTypeEnum.SUBSCRIBE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        errors = ValidationService.validate_for_publish(task)

        assert len(errors) > 0
        assert any("not compatible" in error for error in errors)

    def test_validate_platform_task_type_combination_valid(self) -> None:
        """Test validating valid platform-task type combination."""
        is_valid, error = (
            ValidationService.validate_platform_task_type_combination(
                PlatformEnum.YOUTUBE, TaskTypeEnum.SUBSCRIBE
            )
        )

        assert is_valid is True
        assert error is None

    def test_validate_platform_task_type_combination_invalid(self) -> None:
        """Test validating invalid platform-task type combination."""
        is_valid, error = (
            ValidationService.validate_platform_task_type_combination(
                PlatformEnum.FACEBOOK, TaskTypeEnum.SUBSCRIBE
            )
        )

        assert is_valid is False
        assert error is not None
        assert "not compatible" in error
        assert "facebook" in error.lower()

    def test_validate_task_update_valid(self) -> None:
        """Test validating valid task update."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            current_performers=10,
            status=TaskStatusEnum.DRAFT,
        )
        update_data = {"budget": Decimal("15.00")}
        errors = ValidationService.validate_task_update(task, update_data)

        assert errors == []

    def test_validate_task_update_negative_budget(self) -> None:
        """Test validating task update with negative budget."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        update_data = {"budget": Decimal("-5.00")}
        errors = ValidationService.validate_task_update(task, update_data)

        assert len(errors) > 0
        assert any("Budget must be positive" in error for error in errors)

    def test_validate_task_update_max_performers_below_current(self) -> None:
        """Test validating update with max_performers below current."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            current_performers=50,
            status=TaskStatusEnum.DRAFT,
        )
        update_data = {"max_performers": 40}
        errors = ValidationService.validate_task_update(task, update_data)

        assert len(errors) > 0
        assert any("cannot be less than current performers" in error for error in errors)

    def test_validate_task_update_platform_change(self) -> None:
        """Test validating task update with platform change."""
        task = Task(
            creator_id="user-123",
            title="Like my post",
            description="Please like my Instagram post",
            instructions="1. Visit URL 2. Click like",
            platform=PlatformEnum.INSTAGRAM,
            task_type=TaskTypeEnum.LIKE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        update_data = {"platform": PlatformEnum.YOUTUBE}
        errors = ValidationService.validate_task_update(task, update_data)

        assert errors == []

    def test_validate_task_update_incompatible_platform(self) -> None:
        """Test validating task update with incompatible platform."""
        task = Task(
            creator_id="user-123",
            title="Subscribe",
            description="Please subscribe",
            instructions="1. Visit URL 2. Click subscribe",
            platform=PlatformEnum.YOUTUBE,
            task_type=TaskTypeEnum.SUBSCRIBE,
            budget=Decimal("10.00"),
            service_fee=Decimal("1.50"),
            total_cost=Decimal("11.50"),
            max_performers=100,
            status=TaskStatusEnum.DRAFT,
        )
        update_data = {"platform": PlatformEnum.FACEBOOK}
        errors = ValidationService.validate_task_update(task, update_data)

        assert len(errors) > 0
        assert any("not compatible" in error for error in errors)

    def test_validate_all_platforms_have_compatible_types(self) -> None:
        """Test that all platforms have at least one compatible task type."""
        for platform in PlatformEnum:
            # At least LIKE should be compatible with all platforms
            is_valid, _ = (
                ValidationService.validate_platform_task_type_combination(
                    platform, TaskTypeEnum.LIKE
                )
            )
            assert is_valid is True

    def test_validate_youtube_subscribe_compatibility(self) -> None:
        """Test YouTube-Subscribe specific compatibility."""
        is_valid, _ = ValidationService.validate_platform_task_type_combination(
            PlatformEnum.YOUTUBE, TaskTypeEnum.SUBSCRIBE
        )
        assert is_valid is True

        is_valid, _ = ValidationService.validate_platform_task_type_combination(
            PlatformEnum.FACEBOOK, TaskTypeEnum.SUBSCRIBE
        )
        assert is_valid is False
