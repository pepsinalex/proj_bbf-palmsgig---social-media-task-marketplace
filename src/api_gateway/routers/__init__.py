"""
API Gateway Routers Package.

This module exports all router instances for easy import and inclusion in the main application.
"""

from src.api_gateway.routers.health import router as health_router

__all__ = ["health_router"]
