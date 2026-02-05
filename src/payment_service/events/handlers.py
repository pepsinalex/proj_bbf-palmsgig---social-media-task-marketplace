"""
Payment Event Handlers.

Handles payment-related events triggered by task lifecycle events including
task completion, verification, and automated payment processing.
"""

import logging
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.schemas.escrow import EscrowReleaseRequest
from src.payment_service.services.escrow_service import EscrowService

logger = logging.getLogger(__name__)


class PaymentEventHandler:
    """
    Handler for payment-related events.

    Processes events from the task service and triggers appropriate
    payment operations including escrow release and automated payments.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize payment event handler.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.escrow_service = EscrowService(session)
        logger.debug("PaymentEventHandler initialized")

    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Handle payment event based on type.

        Args:
            event_type: Type of event
            event_data: Event data payload

        Raises:
            ValueError: If event type is unknown or validation fails
        """
        logger.info(
            "Handling payment event",
            extra={
                "event_type": event_type,
                "event_data": event_data,
            },
        )

        if event_type == "task.completed":
            await self._handle_task_completed(event_data)
        elif event_type == "task.verified":
            await self._handle_task_verified(event_data)
        elif event_type == "task.rejected":
            await self._handle_task_rejected(event_data)
        elif event_type == "task.disputed":
            await self._handle_task_disputed(event_data)
        else:
            logger.warning(
                "Unknown payment event type",
                extra={"event_type": event_type},
            )
            raise ValueError(f"Unknown event type: {event_type}")

    async def _handle_task_completed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle task completed event.

        Logs the task completion for audit purposes. Actual payment
        release happens after verification.

        Args:
            event_data: Event data containing task details
        """
        task_id = event_data.get("task_id")
        worker_id = event_data.get("worker_id")

        logger.info(
            "Task completed - awaiting verification",
            extra={
                "task_id": task_id,
                "worker_id": worker_id,
            },
        )

        # Check if escrow exists for this task
        escrow_status = await self.escrow_service.get_escrow_status(task_id)
        if escrow_status:
            logger.info(
                "Escrow found for completed task",
                extra={
                    "task_id": task_id,
                    "escrow_amount": str(escrow_status.total_amount),
                    "escrow_status": escrow_status.status,
                },
            )
        else:
            logger.warning(
                "No escrow found for completed task",
                extra={"task_id": task_id},
            )

    async def _handle_task_verified(self, event_data: Dict[str, Any]) -> None:
        """
        Handle task verified event.

        Automatically releases escrowed funds to the worker upon
        task verification by the creator.

        Args:
            event_data: Event data containing task and payment details

        Raises:
            ValueError: If required data is missing or validation fails
        """
        task_id = event_data.get("task_id")
        payer_wallet_id = event_data.get("payer_wallet_id")
        payee_wallet_id = event_data.get("payee_wallet_id")
        amount = event_data.get("amount")
        platform_fee_percentage = event_data.get("platform_fee_percentage", 0.05)

        logger.info(
            "Task verified - releasing escrow funds",
            extra={
                "task_id": task_id,
                "payer_wallet_id": payer_wallet_id,
                "payee_wallet_id": payee_wallet_id,
                "amount": str(amount) if amount else None,
            },
        )

        # Validate required fields
        if not all([task_id, payer_wallet_id, payee_wallet_id, amount]):
            logger.error(
                "Missing required fields for escrow release",
                extra={
                    "task_id": task_id,
                    "payer_wallet_id": payer_wallet_id,
                    "payee_wallet_id": payee_wallet_id,
                    "amount": str(amount) if amount else None,
                },
            )
            raise ValueError("Missing required fields for escrow release")

        # Convert amount to Decimal
        try:
            amount_decimal = Decimal(str(amount))
            fee_percentage_decimal = Decimal(str(platform_fee_percentage))
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid amount or fee percentage",
                extra={
                    "task_id": task_id,
                    "amount": str(amount),
                    "platform_fee_percentage": str(platform_fee_percentage),
                    "error": str(e),
                },
            )
            raise ValueError(f"Invalid amount or fee percentage: {str(e)}")

        # Create release request
        release_request = EscrowReleaseRequest(
            task_id=task_id,
            payer_wallet_id=payer_wallet_id,
            payee_wallet_id=payee_wallet_id,
            amount=amount_decimal,
            platform_fee_percentage=fee_percentage_decimal,
        )

        # Release funds from escrow
        try:
            result = await self.escrow_service.release_funds(release_request)
            logger.info(
                "Escrow funds released successfully",
                extra={
                    "task_id": task_id,
                    "transaction_id": result.transaction_id,
                    "amount": str(result.amount),
                    "platform_fee": str(result.platform_fee),
                    "total_amount": str(result.total_amount),
                },
            )
        except ValueError as e:
            logger.error(
                "Failed to release escrow funds",
                extra={
                    "task_id": task_id,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to release escrow funds: {str(e)}")

    async def _handle_task_rejected(self, event_data: Dict[str, Any]) -> None:
        """
        Handle task rejected event.

        Returns escrowed funds to the task creator when a task is rejected.

        Args:
            event_data: Event data containing task details
        """
        task_id = event_data.get("task_id")
        payer_wallet_id = event_data.get("payer_wallet_id")

        logger.info(
            "Task rejected - returning escrow funds to payer",
            extra={
                "task_id": task_id,
                "payer_wallet_id": payer_wallet_id,
            },
        )

        # Get escrow status
        escrow_status = await self.escrow_service.get_escrow_status(task_id)
        if not escrow_status:
            logger.warning(
                "No escrow found for rejected task",
                extra={"task_id": task_id},
            )
            return

        if escrow_status.status != "held":
            logger.warning(
                "Escrow not in held status for rejected task",
                extra={
                    "task_id": task_id,
                    "escrow_status": escrow_status.status,
                },
            )
            return

        # Release funds back to payer
        try:
            from src.payment_service.services.wallet_service import WalletService

            wallet_service = WalletService(self.session)
            await wallet_service.release_from_escrow(
                payer_wallet_id,
                escrow_status.total_amount,
                description=f"Refund for rejected task {task_id}",
            )

            logger.info(
                "Escrow funds returned to payer",
                extra={
                    "task_id": task_id,
                    "payer_wallet_id": payer_wallet_id,
                    "amount": str(escrow_status.total_amount),
                },
            )
        except ValueError as e:
            logger.error(
                "Failed to return escrow funds to payer",
                extra={
                    "task_id": task_id,
                    "payer_wallet_id": payer_wallet_id,
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to return escrow funds: {str(e)}")

    async def _handle_task_disputed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle task disputed event.

        Freezes escrow funds pending dispute resolution.

        Args:
            event_data: Event data containing task and dispute details
        """
        task_id = event_data.get("task_id")
        dispute_id = event_data.get("dispute_id")
        dispute_reason = event_data.get("dispute_reason")

        logger.warning(
            "Task disputed - escrow funds frozen pending resolution",
            extra={
                "task_id": task_id,
                "dispute_id": dispute_id,
                "dispute_reason": dispute_reason,
            },
        )

        # Get escrow status
        escrow_status = await self.escrow_service.get_escrow_status(task_id)
        if escrow_status:
            logger.warning(
                "Escrow frozen for disputed task",
                extra={
                    "task_id": task_id,
                    "dispute_id": dispute_id,
                    "escrow_amount": str(escrow_status.total_amount),
                },
            )
        else:
            logger.error(
                "No escrow found for disputed task",
                extra={
                    "task_id": task_id,
                    "dispute_id": dispute_id,
                },
            )


async def handle_task_completed(session: AsyncSession, event_data: Dict[str, Any]) -> None:
    """
    Convenience function to handle task completed event.

    Args:
        session: SQLAlchemy async session
        event_data: Event data
    """
    handler = PaymentEventHandler(session)
    await handler.handle_event("task.completed", event_data)


async def handle_task_verified(session: AsyncSession, event_data: Dict[str, Any]) -> None:
    """
    Convenience function to handle task verified event.

    Args:
        session: SQLAlchemy async session
        event_data: Event data
    """
    handler = PaymentEventHandler(session)
    await handler.handle_event("task.verified", event_data)
