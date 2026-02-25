"""
API v1 Router.

Aggregates all v1 service routers and provides versioned API endpoints.
"""

import logging

from fastapi import APIRouter

from src.task_management.routers import assignment
from src.user_management.routers import auth_router, mfa_router, oauth_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["API v1"])

router.include_router(auth_router, tags=["User Authentication"])
router.include_router(oauth_router, tags=["OAuth Authentication"])
router.include_router(mfa_router, tags=["Multi-Factor Authentication"])
router.include_router(assignment.router, prefix="/assignments", tags=["assignments"])

logger.info(
    "API v1 router configured with authentication, OAuth, MFA, and assignment endpoints"
)
