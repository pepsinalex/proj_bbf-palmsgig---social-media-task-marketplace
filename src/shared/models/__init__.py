"""
Models package initialization.

Imports all models for Alembic discovery and exports common model classes.
This ensures all models are registered with SQLAlchemy before migrations run.
"""

from src.shared.models.auth import AuditLog, AuthenticationMethod, RefreshToken
from src.shared.models.base import Base, BaseModel, SoftDeleteMixin, TimestampMixin
from src.shared.models.user import User

__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "User",
    "AuthenticationMethod",
    "RefreshToken",
    "AuditLog",
]
