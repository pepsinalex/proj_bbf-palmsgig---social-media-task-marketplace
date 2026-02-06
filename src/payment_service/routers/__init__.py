"""
Payment Service Routers.

This module exports all API routers for payment management.
"""

from src.payment_service.routers.escrow import router as escrow_router
from src.payment_service.routers.paypal import router as paypal_router
from src.payment_service.routers.stripe import router as stripe_router
from src.payment_service.routers.transaction import router as transaction_router
from src.payment_service.routers.wallet import router as wallet_router

__all__ = [
    "wallet_router",
    "transaction_router",
    "stripe_router",
    "paypal_router",
    "escrow_router",
]
