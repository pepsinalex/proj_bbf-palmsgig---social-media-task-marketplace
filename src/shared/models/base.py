"""
Base model class with common fields and audit functionality.

This module provides SQLAlchemy declarative base, base model class with common fields,
and mixins for timestamps and soft delete functionality.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


class TimestampMixin:
    """
    Mixin for timestamp fields.

    Adds created_at and updated_at fields to models.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Adds deleted_at field and is_deleted property to models.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """
        Check if the record is soft deleted.

        Returns:
            True if deleted_at is set, False otherwise
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """
        Soft delete the record by setting deleted_at timestamp.
        """
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """
        Restore a soft deleted record by clearing deleted_at timestamp.
        """
        self.deleted_at = None


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields.

    Provides:
    - UUID primary key (id)
    - Timestamp fields (created_at, updated_at)
    - String representation
    - Dictionary conversion

    All application models should inherit from this base class.
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    def __repr__(self) -> str:
        """
        Return string representation of the model.

        Returns:
            String representation with class name and ID

        Example:
            >>> user = User(id="123", email="test@example.com")
            >>> repr(user)
            '<User(id=123)>'
        """
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model

        Example:
            >>> user = User(id="123", email="test@example.com")
            >>> user.to_dict()
            {'id': '123', 'email': 'test@example.com', ...}
        """
        result: dict[str, Any] = {}

        for column in self.__table__.columns:
            value = getattr(self, column.name)

            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseModel":
        """
        Create model instance from dictionary.

        Args:
            data: Dictionary with model field values

        Returns:
            New model instance

        Example:
            >>> data = {'email': 'test@example.com', 'username': 'testuser'}
            >>> user = User.from_dict(data)
        """
        return cls(**data)
