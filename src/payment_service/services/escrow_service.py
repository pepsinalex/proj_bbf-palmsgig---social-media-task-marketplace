"""
Escrow Service.

Provides business logic for escrow management including holding funds,
releasing funds, and handling disputes with proper validation and error handling.
"""

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.transaction import Transaction, TransactionStatus, TransactionType
from src.payment_service.models.wallet import Wallet
from src.payment_service.schemas.escrow import (
    EscrowHoldRequest,
    EscrowReleaseRequest,
    EscrowResponse,
)
from src.payment_service.services.wallet_service import WalletService

logger = logging.getLogger(__name__)


class EscrowService:
    """
    Service class for escrow management operations.

    Handles all business logic for escrow operations including holding funds,
    releasing funds, and handling dispute resolution with proper validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize escrow service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.wallet_service = WalletService(session)
        logger.debug("EscrowService initialized")

    async def hold_funds(self, request: EscrowHoldRequest) -> EscrowResponse:
        """
        Hold funds in escrow for a task payment.

        Moves funds from the payer's available balance to escrow balance
        and creates a transaction record.

        Args:
            request: Escrow hold request data

        Returns:
            EscrowResponse with escrow details

        Raises:
            ValueError: If wallet not found, insufficient balance, or validation fails
        """
        logger.info(
            "Holding funds in escrow",
            extra={
                "task_id": request.task_id,
                "payer_wallet_id": request.payer_wallet_id,
                "amount": str(request.amount),
            },
        )

        # Get payer wallet
        payer_wallet = await self.wallet_service.get_wallet(request.payer_wallet_id)
        if not payer_wallet:
            logger.error(
                "Payer wallet not found for escrow hold",
                extra={"wallet_id": request.payer_wallet_id},
            )
            raise ValueError(f"Payer wallet not found: {request.payer_wallet_id}")

        # Validate sufficient balance
        if not payer_wallet.can_transact(request.amount):
            logger.error(
                "Insufficient balance for escrow hold",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "balance": str(payer_wallet.balance),
                    "required": str(request.amount),
                },
            )
            raise ValueError("Insufficient balance for escrow hold")

        # Calculate platform fee
        platform_fee = request.amount * request.platform_fee_percentage
        total_amount = request.amount + platform_fee

        logger.info(
            "Escrow hold calculation",
            extra={
                "task_id": request.task_id,
                "base_amount": str(request.amount),
                "platform_fee": str(platform_fee),
                "total_amount": str(total_amount),
            },
        )

        # Validate total amount availability
        if payer_wallet.balance < total_amount:
            logger.error(
                "Insufficient balance for total escrow amount including fees",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "balance": str(payer_wallet.balance),
                    "required_total": str(total_amount),
                },
            )
            raise ValueError(
                f"Insufficient balance for total amount including fees. "
                f"Required: {total_amount}, Available: {payer_wallet.balance}"
            )

        # Move funds to escrow
        try:
            await self.wallet_service.move_to_escrow(
                request.payer_wallet_id,
                total_amount,
                description=f"Escrow hold for task {request.task_id}",
            )
        except ValueError as e:
            logger.error(
                "Failed to move funds to escrow",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "amount": str(total_amount),
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to hold funds in escrow: {str(e)}")

        # Create escrow transaction record
        transaction = Transaction(
            wallet_id=request.payer_wallet_id,
            type=TransactionType.PAYMENT.value,
            amount=total_amount,
            currency=payer_wallet.currency,
            status=TransactionStatus.PENDING.value,
            description=f"Escrow hold for task {request.task_id}",
            metadata={
                "task_id": request.task_id,
                "payee_wallet_id": request.payee_wallet_id,
                "base_amount": str(request.amount),
                "platform_fee": str(platform_fee),
                "platform_fee_percentage": str(request.platform_fee_percentage),
                "escrow_type": "hold",
            },
        )

        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(
            "Funds held in escrow successfully",
            extra={
                "task_id": request.task_id,
                "transaction_id": transaction.id,
                "amount": str(total_amount),
            },
        )

        return EscrowResponse(
            task_id=request.task_id,
            payer_wallet_id=request.payer_wallet_id,
            payee_wallet_id=request.payee_wallet_id,
            amount=request.amount,
            platform_fee=platform_fee,
            total_amount=total_amount,
            status="held",
            transaction_id=transaction.id,
        )

    async def release_funds(self, request: EscrowReleaseRequest) -> EscrowResponse:
        """
        Release funds from escrow to payee.

        Releases funds from payer's escrow to payee's available balance,
        applies platform fee, and updates transaction status.

        Args:
            request: Escrow release request data

        Returns:
            EscrowResponse with release details

        Raises:
            ValueError: If wallets not found, insufficient escrow, or validation fails
        """
        logger.info(
            "Releasing funds from escrow",
            extra={
                "task_id": request.task_id,
                "payer_wallet_id": request.payer_wallet_id,
                "payee_wallet_id": request.payee_wallet_id,
                "amount": str(request.amount),
            },
        )

        # Get payer wallet
        payer_wallet = await self.wallet_service.get_wallet(request.payer_wallet_id)
        if not payer_wallet:
            logger.error(
                "Payer wallet not found for escrow release",
                extra={"wallet_id": request.payer_wallet_id},
            )
            raise ValueError(f"Payer wallet not found: {request.payer_wallet_id}")

        # Get payee wallet
        payee_wallet = await self.wallet_service.get_wallet(request.payee_wallet_id)
        if not payee_wallet:
            logger.error(
                "Payee wallet not found for escrow release",
                extra={"wallet_id": request.payee_wallet_id},
            )
            raise ValueError(f"Payee wallet not found: {request.payee_wallet_id}")

        # Calculate platform fee
        platform_fee = request.amount * request.platform_fee_percentage
        total_amount = request.amount + platform_fee
        payee_amount = request.amount

        logger.info(
            "Escrow release calculation",
            extra={
                "task_id": request.task_id,
                "base_amount": str(request.amount),
                "platform_fee": str(platform_fee),
                "total_escrow_amount": str(total_amount),
                "payee_receives": str(payee_amount),
            },
        )

        # Validate payer has sufficient escrow balance
        if payer_wallet.escrow_balance < total_amount:
            logger.error(
                "Insufficient escrow balance for release",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "escrow_balance": str(payer_wallet.escrow_balance),
                    "required": str(total_amount),
                },
            )
            raise ValueError(
                f"Insufficient escrow balance. "
                f"Required: {total_amount}, Available: {payer_wallet.escrow_balance}"
            )

        # Release funds from payer's escrow (this adds back to payer's available balance)
        try:
            await self.wallet_service.release_from_escrow(
                request.payer_wallet_id,
                total_amount,
                description=f"Escrow release for task {request.task_id}",
            )
        except ValueError as e:
            logger.error(
                "Failed to release funds from payer escrow",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "amount": str(total_amount),
                    "error": str(e),
                },
            )
            raise ValueError(f"Failed to release funds from escrow: {str(e)}")

        # Deduct total amount from payer (payment + fee)
        try:
            await self.wallet_service.deduct_balance(
                request.payer_wallet_id,
                total_amount,
                description=f"Payment for task {request.task_id}",
            )
        except ValueError as e:
            logger.error(
                "Failed to deduct payment from payer",
                extra={
                    "wallet_id": request.payer_wallet_id,
                    "amount": str(total_amount),
                    "error": str(e),
                },
            )
            # Rollback escrow release if deduction fails
            await self.wallet_service.move_to_escrow(
                request.payer_wallet_id,
                total_amount,
                description=f"Rollback escrow release for task {request.task_id}",
            )
            raise ValueError(f"Failed to process payment: {str(e)}")

        # Add payment amount to payee (without platform fee)
        try:
            await self.wallet_service.add_balance(
                request.payee_wallet_id,
                payee_amount,
                description=f"Payment received for task {request.task_id}",
            )
        except ValueError as e:
            logger.error(
                "Failed to add payment to payee",
                extra={
                    "wallet_id": request.payee_wallet_id,
                    "amount": str(payee_amount),
                    "error": str(e),
                },
            )
            # Rollback previous operations
            await self.wallet_service.add_balance(
                request.payer_wallet_id,
                total_amount,
                description=f"Rollback payment for task {request.task_id}",
            )
            await self.wallet_service.move_to_escrow(
                request.payer_wallet_id,
                total_amount,
                description=f"Rollback escrow release for task {request.task_id}",
            )
            raise ValueError(f"Failed to transfer payment to payee: {str(e)}")

        # Create release transaction records
        # Transaction for payer
        payer_transaction = Transaction(
            wallet_id=request.payer_wallet_id,
            type=TransactionType.PAYMENT.value,
            amount=total_amount,
            currency=payer_wallet.currency,
            status=TransactionStatus.COMPLETED.value,
            description=f"Payment for task {request.task_id}",
            metadata={
                "task_id": request.task_id,
                "payee_wallet_id": request.payee_wallet_id,
                "base_amount": str(request.amount),
                "platform_fee": str(platform_fee),
                "platform_fee_percentage": str(request.platform_fee_percentage),
                "escrow_type": "release",
                "transaction_type": "payment",
            },
        )

        # Transaction for payee
        payee_transaction = Transaction(
            wallet_id=request.payee_wallet_id,
            type=TransactionType.DEPOSIT.value,
            amount=payee_amount,
            currency=payee_wallet.currency,
            status=TransactionStatus.COMPLETED.value,
            description=f"Payment received for task {request.task_id}",
            metadata={
                "task_id": request.task_id,
                "payer_wallet_id": request.payer_wallet_id,
                "base_amount": str(request.amount),
                "escrow_type": "release",
                "transaction_type": "receipt",
            },
        )

        self.session.add(payer_transaction)
        self.session.add(payee_transaction)
        await self.session.commit()
        await self.session.refresh(payer_transaction)
        await self.session.refresh(payee_transaction)

        logger.info(
            "Funds released from escrow successfully",
            extra={
                "task_id": request.task_id,
                "payer_transaction_id": payer_transaction.id,
                "payee_transaction_id": payee_transaction.id,
                "total_amount": str(total_amount),
                "payee_received": str(payee_amount),
                "platform_fee": str(platform_fee),
            },
        )

        return EscrowResponse(
            task_id=request.task_id,
            payer_wallet_id=request.payer_wallet_id,
            payee_wallet_id=request.payee_wallet_id,
            amount=request.amount,
            platform_fee=platform_fee,
            total_amount=total_amount,
            status="released",
            transaction_id=payer_transaction.id,
        )

    async def get_escrow_status(self, task_id: str) -> Optional[EscrowResponse]:
        """
        Get escrow status for a task.

        Args:
            task_id: Task ID

        Returns:
            EscrowResponse with current status or None if not found
        """
        logger.debug("Getting escrow status", extra={"task_id": task_id})

        # Find escrow transaction for task
        query = (
            select(Transaction)
            .where(Transaction.metadata["task_id"].astext == task_id)
            .where(Transaction.type == TransactionType.PAYMENT.value)
            .order_by(Transaction.created_at.desc())
        )

        result = await self.session.execute(query)
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(
                "No escrow transaction found for task",
                extra={"task_id": task_id},
            )
            return None

        metadata = transaction.metadata or {}
        status = "held" if transaction.status == TransactionStatus.PENDING.value else "released"

        response = EscrowResponse(
            task_id=task_id,
            payer_wallet_id=transaction.wallet_id,
            payee_wallet_id=metadata.get("payee_wallet_id", ""),
            amount=Decimal(metadata.get("base_amount", "0")),
            platform_fee=Decimal(metadata.get("platform_fee", "0")),
            total_amount=transaction.amount,
            status=status,
            transaction_id=transaction.id,
        )

        logger.debug(
            "Escrow status retrieved",
            extra={
                "task_id": task_id,
                "status": status,
                "transaction_id": transaction.id,
            },
        )

        return response
