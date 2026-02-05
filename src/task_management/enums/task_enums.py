"""
Task Management Enums.

Provides enum classes for platforms, task types, and task statuses
with validation methods for platform-specific task type compatibility.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PlatformEnum(str, Enum):
    """
    Supported social media platforms.

    Each platform has specific task types that are compatible with it.
    """

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"

    @classmethod
    def values(cls) -> list[str]:
        """Get all platform values."""
        return [platform.value for platform in cls]

    @classmethod
    def from_string(cls, value: str) -> "PlatformEnum":
        """
        Convert string to PlatformEnum.

        Args:
            value: Platform string value

        Returns:
            PlatformEnum instance

        Raises:
            ValueError: If platform is invalid
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_platforms = ", ".join(cls.values())
            raise ValueError(
                f"Invalid platform: {value}. "
                f"Valid platforms: {valid_platforms}"
            )


class TaskTypeEnum(str, Enum):
    """
    Types of social media tasks.

    Different task types are compatible with different platforms.
    """

    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    FOLLOW = "follow"
    VIEW = "view"
    SUBSCRIBE = "subscribe"
    ENGAGEMENT = "engagement"

    @classmethod
    def values(cls) -> list[str]:
        """Get all task type values."""
        return [task_type.value for task_type in cls]

    @classmethod
    def from_string(cls, value: str) -> "TaskTypeEnum":
        """
        Convert string to TaskTypeEnum.

        Args:
            value: Task type string value

        Returns:
            TaskTypeEnum instance

        Raises:
            ValueError: If task type is invalid
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_types = ", ".join(cls.values())
            raise ValueError(
                f"Invalid task type: {value}. Valid types: {valid_types}"
            )


class TaskStatusEnum(str, Enum):
    """
    Task lifecycle statuses.

    Represents the various states a task can be in throughout its lifecycle.
    """

    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    @classmethod
    def values(cls) -> list[str]:
        """Get all status values."""
        return [status.value for status in cls]

    @classmethod
    def from_string(cls, value: str) -> "TaskStatusEnum":
        """
        Convert string to TaskStatusEnum.

        Args:
            value: Status string value

        Returns:
            TaskStatusEnum instance

        Raises:
            ValueError: If status is invalid
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_statuses = ", ".join(cls.values())
            raise ValueError(
                f"Invalid status: {value}. Valid statuses: {valid_statuses}"
            )

    def can_transition_to(self, new_status: "TaskStatusEnum") -> bool:
        """
        Check if transition to new status is valid.

        Args:
            new_status: Target status

        Returns:
            True if transition is allowed, False otherwise
        """
        # Define valid transitions
        valid_transitions = {
            TaskStatusEnum.DRAFT: {
                TaskStatusEnum.PENDING_PAYMENT,
                TaskStatusEnum.CANCELLED,
            },
            TaskStatusEnum.PENDING_PAYMENT: {
                TaskStatusEnum.ACTIVE,
                TaskStatusEnum.CANCELLED,
            },
            TaskStatusEnum.ACTIVE: {
                TaskStatusEnum.PAUSED,
                TaskStatusEnum.COMPLETED,
                TaskStatusEnum.CANCELLED,
                TaskStatusEnum.EXPIRED,
            },
            TaskStatusEnum.PAUSED: {
                TaskStatusEnum.ACTIVE,
                TaskStatusEnum.CANCELLED,
                TaskStatusEnum.EXPIRED,
            },
            TaskStatusEnum.COMPLETED: set(),
            TaskStatusEnum.CANCELLED: set(),
            TaskStatusEnum.EXPIRED: set(),
        }

        return new_status in valid_transitions.get(self, set())


# Platform-specific task type compatibility mapping
PLATFORM_TASK_TYPE_COMPATIBILITY = {
    PlatformEnum.FACEBOOK: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.FOLLOW,
        TaskTypeEnum.ENGAGEMENT,
    },
    PlatformEnum.INSTAGRAM: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.FOLLOW,
        TaskTypeEnum.VIEW,
        TaskTypeEnum.ENGAGEMENT,
    },
    PlatformEnum.TWITTER: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.FOLLOW,
        TaskTypeEnum.ENGAGEMENT,
    },
    PlatformEnum.TIKTOK: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.FOLLOW,
        TaskTypeEnum.VIEW,
        TaskTypeEnum.ENGAGEMENT,
    },
    PlatformEnum.YOUTUBE: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.SUBSCRIBE,
        TaskTypeEnum.VIEW,
        TaskTypeEnum.ENGAGEMENT,
    },
    PlatformEnum.LINKEDIN: {
        TaskTypeEnum.LIKE,
        TaskTypeEnum.COMMENT,
        TaskTypeEnum.SHARE,
        TaskTypeEnum.FOLLOW,
        TaskTypeEnum.ENGAGEMENT,
    },
}


def validate_platform_task_type(
    platform: PlatformEnum, task_type: TaskTypeEnum
) -> bool:
    """
    Validate if a task type is compatible with a platform.

    Args:
        platform: Social media platform
        task_type: Type of task

    Returns:
        True if compatible, False otherwise

    Example:
        >>> validate_platform_task_type(
        ...     PlatformEnum.YOUTUBE,
        ...     TaskTypeEnum.SUBSCRIBE
        ... )
        True
        >>> validate_platform_task_type(
        ...     PlatformEnum.YOUTUBE,
        ...     TaskTypeEnum.FOLLOW
        ... )
        False
    """
    compatible_types = PLATFORM_TASK_TYPE_COMPATIBILITY.get(platform, set())
    is_valid = task_type in compatible_types

    if not is_valid:
        logger.warning(
            "Invalid platform-task type combination",
            extra={
                "platform": platform.value,
                "task_type": task_type.value,
                "valid_types": [t.value for t in compatible_types],
            },
        )

    return is_valid


def get_compatible_task_types(platform: PlatformEnum) -> set[TaskTypeEnum]:
    """
    Get all task types compatible with a platform.

    Args:
        platform: Social media platform

    Returns:
        Set of compatible task types

    Example:
        >>> types = get_compatible_task_types(PlatformEnum.YOUTUBE)
        >>> TaskTypeEnum.SUBSCRIBE in types
        True
    """
    return PLATFORM_TASK_TYPE_COMPATIBILITY.get(platform, set())
