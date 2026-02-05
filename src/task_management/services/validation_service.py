"""
Validation Service.

Provides validation logic for task drafts and publishing with
platform-specific rules and comprehensive error messaging.
"""

import logging
from typing import Any

from src.task_management.enums.task_enums import (
    PlatformEnum,
    TaskTypeEnum,
    validate_platform_task_type,
)
from src.task_management.models.task import Task

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class ValidationService:
    """
    Service class for task validation.

    Handles validation of task drafts and publishing requirements with
    platform-specific rules and comprehensive error reporting.
    """

    @staticmethod
    def validate_draft(task_data: dict[str, Any]) -> list[str]:
        """
        Validate task draft data.

        Drafts have relaxed validation - only basic checks are performed.
        Returns list of validation errors (empty if valid).

        Args:
            task_data: Task draft data dictionary

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> errors = ValidationService.validate_draft({
            ...     "title": "My Task",
            ...     "budget": Decimal("10.00")
            ... })
            >>> len(errors) == 0
            True
        """
        errors = []

        # Title is required and must be non-empty
        title = task_data.get("title", "").strip()
        if not title:
            errors.append("Title is required")
        elif len(title) < 3:
            errors.append("Title must be at least 3 characters")
        elif len(title) > 255:
            errors.append("Title must not exceed 255 characters")

        # If platform and task_type are both provided, validate compatibility
        platform = task_data.get("platform")
        task_type = task_data.get("task_type")

        if platform and task_type:
            try:
                if isinstance(platform, str):
                    platform = PlatformEnum(platform)
                if isinstance(task_type, str):
                    task_type = TaskTypeEnum(task_type)

                if not validate_platform_task_type(platform, task_type):
                    errors.append(
                        f"Task type '{task_type.value}' is not compatible "
                        f"with platform '{platform.value}'"
                    )
            except ValueError as e:
                errors.append(str(e))

        # Validate budget if provided
        budget = task_data.get("budget")
        if budget is not None:
            try:
                if budget <= 0:
                    errors.append("Budget must be positive")
            except (TypeError, ValueError):
                errors.append("Budget must be a valid number")

        # Validate max_performers if provided
        max_performers = task_data.get("max_performers")
        if max_performers is not None:
            try:
                if max_performers <= 0:
                    errors.append("Max performers must be positive")
                elif max_performers > 10000:
                    errors.append("Max performers cannot exceed 10,000")
            except (TypeError, ValueError):
                errors.append("Max performers must be a valid integer")

        if errors:
            logger.warning(
                "Draft validation failed",
                extra={
                    "errors": errors,
                    "title": task_data.get("title"),
                },
            )
        else:
            logger.debug("Draft validation passed")

        return errors

    @staticmethod
    def validate_for_publish(task: Task) -> list[str]:
        """
        Validate task is ready for publishing.

        All required fields must be present and valid for publishing.
        Returns list of validation errors (empty if valid).

        Args:
            task: Task instance to validate

        Returns:
            List of validation error messages (empty if valid)

        Raises:
            ValidationError: If task cannot be published

        Example:
            >>> task = Task(...)
            >>> errors = ValidationService.validate_for_publish(task)
            >>> if errors:
            ...     raise ValidationError("; ".join(errors))
        """
        errors = []

        # Required fields validation
        if not task.title or not task.title.strip():
            errors.append("Title is required")
        elif len(task.title.strip()) < 3:
            errors.append("Title must be at least 3 characters")

        if not task.description or not task.description.strip():
            errors.append("Description is required")
        elif len(task.description.strip()) < 10:
            errors.append("Description must be at least 10 characters")

        if not task.instructions or not task.instructions.strip():
            errors.append("Instructions are required")
        elif len(task.instructions.strip()) < 10:
            errors.append("Instructions must be at least 10 characters")

        if not task.platform:
            errors.append("Platform is required")

        if not task.task_type:
            errors.append("Task type is required")

        if not task.budget or task.budget <= 0:
            errors.append("Budget is required and must be positive")

        if not task.max_performers or task.max_performers <= 0:
            errors.append("Max performers is required and must be positive")

        # Platform-task type compatibility
        if task.platform and task.task_type:
            if not validate_platform_task_type(task.platform, task.task_type):
                errors.append(
                    f"Task type '{task.task_type.value}' is not compatible "
                    f"with platform '{task.platform.value}'"
                )

        if errors:
            logger.warning(
                "Task publish validation failed",
                extra={
                    "task_id": task.id,
                    "errors": errors,
                },
            )
        else:
            logger.info(
                "Task publish validation passed",
                extra={"task_id": task.id},
            )

        return errors

    @staticmethod
    def validate_platform_task_type_combination(
        platform: PlatformEnum, task_type: TaskTypeEnum
    ) -> tuple[bool, str | None]:
        """
        Validate platform and task type combination.

        Args:
            platform: Social media platform
            task_type: Type of task

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> valid, error = ValidationService.\
            ...     validate_platform_task_type_combination(
            ...         PlatformEnum.YOUTUBE,
            ...         TaskTypeEnum.SUBSCRIBE
            ...     )
            >>> valid
            True
            >>> error is None
            True
        """
        is_valid = validate_platform_task_type(platform, task_type)

        if not is_valid:
            error_message = (
                f"Task type '{task_type.value}' is not compatible with "
                f"platform '{platform.value}'. Valid task types for "
                f"{platform.value}: "
            )

            from src.task_management.enums.task_enums import (
                get_compatible_task_types,
            )

            compatible_types = get_compatible_task_types(platform)
            valid_types = ", ".join(sorted([t.value for t in compatible_types]))
            error_message += valid_types

            logger.warning(
                "Platform-task type validation failed",
                extra={
                    "platform": platform.value,
                    "task_type": task_type.value,
                    "valid_types": valid_types,
                },
            )

            return False, error_message

        return True, None

    @staticmethod
    def validate_task_update(
        task: Task, update_data: dict[str, Any]
    ) -> list[str]:
        """
        Validate task update data.

        Args:
            task: Existing task instance
            update_data: Update data dictionary

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> task = Task(...)
            >>> errors = ValidationService.validate_task_update(
            ...     task,
            ...     {"budget": Decimal("20.00")}
            ... )
        """
        errors = []

        # Validate platform-task type compatibility if either is being updated
        new_platform = update_data.get("platform", task.platform)
        new_task_type = update_data.get("task_type", task.task_type)

        if new_platform and new_task_type:
            if isinstance(new_platform, str):
                try:
                    new_platform = PlatformEnum(new_platform)
                except ValueError as e:
                    errors.append(str(e))
                    new_platform = None

            if isinstance(new_task_type, str):
                try:
                    new_task_type = TaskTypeEnum(new_task_type)
                except ValueError as e:
                    errors.append(str(e))
                    new_task_type = None

            if new_platform and new_task_type:
                is_valid, error_msg = (
                    ValidationService.validate_platform_task_type_combination(
                        new_platform, new_task_type
                    )
                )
                if not is_valid and error_msg:
                    errors.append(error_msg)

        # Validate budget if being updated
        if "budget" in update_data:
            budget = update_data["budget"]
            if budget is not None and budget <= 0:
                errors.append("Budget must be positive")

        # Validate max_performers if being updated
        if "max_performers" in update_data:
            max_performers = update_data["max_performers"]
            if max_performers is not None:
                if max_performers <= 0:
                    errors.append("Max performers must be positive")
                elif max_performers > 10000:
                    errors.append("Max performers cannot exceed 10,000")
                elif max_performers < task.current_performers:
                    errors.append(
                        f"Max performers ({max_performers}) cannot be less "
                        f"than current performers ({task.current_performers})"
                    )

        if errors:
            logger.warning(
                "Task update validation failed",
                extra={
                    "task_id": task.id,
                    "errors": errors,
                },
            )

        return errors
