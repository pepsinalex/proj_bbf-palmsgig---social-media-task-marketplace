"""
User Management Routers Package.

This module exports router instances for API Gateway inclusion.
"""

from src.user_management.routers.auth import router as auth_router
from src.user_management.routers.oauth import router as oauth_router

__all__ = [
    "auth_router",
    "oauth_router",
]
