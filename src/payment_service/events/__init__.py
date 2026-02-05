"""
Payment Service Events Package.

Provides event handling classes and processors for payment-related events
including task completion, verification, and automated payment processing.
"""

from src.payment_service.events.handlers import (
    PaymentEventHandler,
    handle_task_completed,
    handle_task_verified,
)

__all__ = [
    "PaymentEventHandler",
    "handle_task_completed",
    "handle_task_verified",
]
