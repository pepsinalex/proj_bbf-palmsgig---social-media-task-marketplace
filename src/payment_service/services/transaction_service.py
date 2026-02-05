"""
Transaction Service.

Provides business logic for transaction management including creation,
status updates, and querying with proper validation and error handling.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.transaction import Transaction, TransactionStatus, TransactionType
from src.payment_service.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionResponse,
    TransactionUpdate,
)

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Service class for transaction management operations.

    Handles all business logic for transactions including creation, updates,
    and querying with proper validation and status management.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize transaction service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.debug("TransactionService initialized")

    def _generate_reference(self) -> str:
        """
        Generate a unique transaction reference.

        Returns:
            Unique transaction reference string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"TXN-{timestamp}-{unique_id}"

    async def create_transaction(self, transaction_data: TransactionCreate) -> Transaction:
        """
        Create a new transaction.

        Args:
            transaction_data: Transaction creation data

        Returns:
            Created transaction instance

        Raises:
            ValueError: If validation fails
        """
        # Generate reference if not provided
        reference = transaction_data.reference or self._generate_reference()

        logger.info(
            "Creating new transaction",
            extra={
                "wallet_id": transaction_data.wallet_id,
                "type": transaction_data.type.value,
                "amount": str(transaction_data.amount),
                "currency": transaction_data.currency,
                "reference": reference,
            },
        )

        # Check for duplicate reference
        existing = await self.get_transaction_by_reference(reference)
        if existing:
            logger.error(
                "Transaction creation failed: duplicate reference",
                extra={"reference": reference},
            )
            raise ValueError(f"Transaction with reference {reference} already exists")

        # Create transaction instance
        transaction = Transaction(
            wallet_id=transaction_data.wallet_id,
            type=transaction_data.type.value,
            amount=transaction_data.amount,
            currency=transaction_data.currency,
            status=TransactionStatus.PENDING.value,
            reference=reference,
            gateway_reference=transaction_data.gateway_reference,
            metadata=transaction_data.metadata,
            description=transaction_data.description,
        )

        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(
            "Transaction created successfully",
            extra={
                "transaction_id": transaction.id,
                "wallet_id": transaction.wallet_id,
                "reference": reference,
                "type": transaction.type,
                "amount": str(transaction.amount),
            },
        )

        return transaction

    async def get_transaction(self, transaction_id: str) -> Transaction | None:
        """
        Get a transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction instance or None if not found
        """
        logger.debug("Fetching transaction by ID", extra={"transaction_id": transaction_id})

        query = select(Transaction).where(Transaction.id == transaction_id)
        result = await self.session.execute(query)
        transaction = result.scalar_one_or_none()

        if transaction:
            logger.debug(
                "Transaction found",
                extra={
                    "transaction_id": transaction_id,
                    "wallet_id": transaction.wallet_id,
                    "status": transaction.status,
                },
            )
        else:
            logger.warning("Transaction not found", extra={"transaction_id": transaction_id})

        return transaction

    async def get_transaction_by_reference(self, reference: str) -> Transaction | None:
        """
        Get a transaction by reference.

        Args:
            reference: Transaction reference

        Returns:
            Transaction instance or None if not found
        """
        logger.debug("Fetching transaction by reference", extra={"reference": reference})

        query = select(Transaction).where(Transaction.reference == reference)
        result = await self.session.execute(query)
        transaction = result.scalar_one_or_none()

        if transaction:
            logger.debug(
                "Transaction found by reference",
                extra={
                    "transaction_id": transaction.id,
                    "reference": reference,
                    "status": transaction.status,
                },
            )
        else:
            logger.warning("Transaction not found by reference", extra={"reference": reference})

        return transaction

    async def update_transaction(
        self, transaction_id: str, transaction_data: TransactionUpdate
    ) -> Transaction | None:
        """
        Update transaction details.

        Args:
            transaction_id: Transaction ID
            transaction_data: Updated transaction data

        Returns:
            Updated transaction instance or None if not found

        Raises:
            ValueError: If update is not allowed
        """
        logger.info(
            "Updating transaction",
            extra={
                "transaction_id": transaction_id,
                "update_data": transaction_data.model_dump(exclude_none=True),
            },
        )

        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            logger.warning(
                "Transaction not found for update", extra={"transaction_id": transaction_id}
            )
            return None

        # Update fields if provided
        if transaction_data.status is not None:
            old_status = transaction.status
            transaction.status = transaction_data.status.value
            logger.info(
                "Transaction status updated",
                extra={
                    "transaction_id": transaction_id,
                    "old_status": old_status,
                    "new_status": transaction.status,
                },
            )

        if transaction_data.gateway_reference is not None:
            transaction.gateway_reference = transaction_data.gateway_reference

        if transaction_data.metadata is not None:
            if transaction.metadata:
                transaction.metadata.update(transaction_data.metadata)
            else:
                transaction.metadata = transaction_data.metadata

        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info("Transaction updated successfully", extra={"transaction_id": transaction_id})

        return transaction

    async def mark_as_processing(self, transaction_id: str) -> Transaction | None:
        """
        Mark transaction as processing.

        Args:
            transaction_id: Transaction ID

        Returns:
            Updated transaction instance or None if not found

        Raises:
            ValueError: If transaction is not in pending status
        """
        logger.info("Marking transaction as processing", extra={"transaction_id": transaction_id})

        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return None

        try:
            transaction.mark_as_processing()
        except ValueError as e:
            logger.error(
                "Failed to mark transaction as processing",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

        await self.session.commit()
        await self.session.refresh(transaction)

        return transaction

    async def mark_as_completed(
        self, transaction_id: str, gateway_reference: str | None = None
    ) -> Transaction | None:
        """
        Mark transaction as completed.

        Args:
            transaction_id: Transaction ID
            gateway_reference: Optional gateway reference

        Returns:
            Updated transaction instance or None if not found

        Raises:
            ValueError: If transaction cannot be completed
        """
        logger.info(
            "Marking transaction as completed",
            extra={
                "transaction_id": transaction_id,
                "gateway_reference": gateway_reference,
            },
        )

        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return None

        try:
            transaction.mark_as_completed(gateway_reference)
        except ValueError as e:
            logger.error(
                "Failed to mark transaction as completed",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

        await self.session.commit()
        await self.session.refresh(transaction)

        return transaction

    async def mark_as_failed(
        self, transaction_id: str, error_message: str | None = None
    ) -> Transaction | None:
        """
        Mark transaction as failed.

        Args:
            transaction_id: Transaction ID
            error_message: Optional error description

        Returns:
            Updated transaction instance or None if not found

        Raises:
            ValueError: If transaction is already completed
        """
        logger.error(
            "Marking transaction as failed",
            extra={
                "transaction_id": transaction_id,
                "error_message": error_message,
            },
        )

        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return None

        try:
            transaction.mark_as_failed(error_message)
        except ValueError as e:
            logger.error(
                "Failed to mark transaction as failed",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

        await self.session.commit()
        await self.session.refresh(transaction)

        return transaction

    async def cancel_transaction(self, transaction_id: str) -> Transaction | None:
        """
        Cancel a pending transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            Updated transaction instance or None if not found

        Raises:
            ValueError: If transaction is not in pending status
        """
        logger.info("Cancelling transaction", extra={"transaction_id": transaction_id})

        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return None

        try:
            transaction.cancel()
        except ValueError as e:
            logger.error(
                "Failed to cancel transaction",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

        await self.session.commit()
        await self.session.refresh(transaction)

        return transaction

    async def list_transactions(
        self,
        wallet_id: str | None = None,
        transaction_type: TransactionType | None = None,
        status: TransactionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TransactionList:
        """
        List transactions with filtering and pagination.

        Args:
            wallet_id: Optional wallet ID filter
            transaction_type: Optional transaction type filter
            status: Optional status filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            TransactionList with paginated results
        """
        logger.debug(
            "Listing transactions",
            extra={
                "wallet_id": wallet_id,
                "transaction_type": transaction_type.value if transaction_type else None,
                "status": status.value if status else None,
                "page": page,
                "page_size": page_size,
            },
        )

        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        # Build query
        conditions = []
        if wallet_id:
            conditions.append(Transaction.wallet_id == wallet_id)
        if transaction_type:
            conditions.append(Transaction.type == transaction_type.value)
        if status:
            conditions.append(Transaction.status == status.value)

        query = select(Transaction)
        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size

        # Get paginated results
        query = query.order_by(desc(Transaction.created_at)).offset(offset).limit(page_size)
        result = await self.session.execute(query)
        transactions = result.scalars().all()

        # Convert to response schemas
        transaction_responses = [
            TransactionResponse.model_validate(txn) for txn in transactions
        ]

        logger.debug(
            "Transactions listed",
            extra={
                "total": total,
                "page": page,
                "page_size": page_size,
                "returned": len(transaction_responses),
            },
        )

        return TransactionList(
            transactions=transaction_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_wallet_transactions(
        self,
        wallet_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> TransactionList:
        """
        Get all transactions for a specific wallet.

        Args:
            wallet_id: Wallet ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            TransactionList with paginated results
        """
        return await self.list_transactions(
            wallet_id=wallet_id,
            page=page,
            page_size=page_size,
        )
