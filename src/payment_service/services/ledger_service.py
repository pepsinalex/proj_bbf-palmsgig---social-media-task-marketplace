"""
Ledger Service.

Provides business logic for double-entry bookkeeping with immutable ledger entries
for proper financial audit trails.
"""

import logging
from decimal import Decimal

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.ledger_entry import AccountType, LedgerEntry

logger = logging.getLogger(__name__)


class LedgerService:
    """
    Service class for ledger management operations.

    Implements double-entry bookkeeping principles with immutable
    ledger entries for financial audit trails.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ledger service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.debug("LedgerService initialized")

    async def create_debit_entry(
        self,
        transaction_id: str,
        account_type: AccountType,
        amount: Decimal,
        balance_after: Decimal,
        description: str | None = None,
    ) -> LedgerEntry:
        """
        Create a debit ledger entry.

        Args:
            transaction_id: Transaction ID
            account_type: Account type
            amount: Debit amount (must be positive)
            balance_after: Balance after this entry
            description: Optional description

        Returns:
            Created ledger entry instance

        Raises:
            ValueError: If amount is not positive
        """
        logger.info(
            "Creating debit ledger entry",
            extra={
                "transaction_id": transaction_id,
                "account_type": account_type.value,
                "amount": str(amount),
                "balance_after": str(balance_after),
            },
        )

        try:
            entry = LedgerEntry.create_debit_entry(
                transaction_id=transaction_id,
                account_type=account_type,
                amount=amount,
                balance_after=balance_after,
                description=description,
            )
        except ValueError as e:
            logger.error(
                "Failed to create debit entry",
                extra={
                    "transaction_id": transaction_id,
                    "account_type": account_type.value,
                    "error": str(e),
                },
            )
            raise

        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)

        logger.info(
            "Debit ledger entry created successfully",
            extra={
                "ledger_entry_id": entry.id,
                "transaction_id": transaction_id,
                "account_type": account_type.value,
            },
        )

        return entry

    async def create_credit_entry(
        self,
        transaction_id: str,
        account_type: AccountType,
        amount: Decimal,
        balance_after: Decimal,
        description: str | None = None,
    ) -> LedgerEntry:
        """
        Create a credit ledger entry.

        Args:
            transaction_id: Transaction ID
            account_type: Account type
            amount: Credit amount (must be positive)
            balance_after: Balance after this entry
            description: Optional description

        Returns:
            Created ledger entry instance

        Raises:
            ValueError: If amount is not positive
        """
        logger.info(
            "Creating credit ledger entry",
            extra={
                "transaction_id": transaction_id,
                "account_type": account_type.value,
                "amount": str(amount),
                "balance_after": str(balance_after),
            },
        )

        try:
            entry = LedgerEntry.create_credit_entry(
                transaction_id=transaction_id,
                account_type=account_type,
                amount=amount,
                balance_after=balance_after,
                description=description,
            )
        except ValueError as e:
            logger.error(
                "Failed to create credit entry",
                extra={
                    "transaction_id": transaction_id,
                    "account_type": account_type.value,
                    "error": str(e),
                },
            )
            raise

        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)

        logger.info(
            "Credit ledger entry created successfully",
            extra={
                "ledger_entry_id": entry.id,
                "transaction_id": transaction_id,
                "account_type": account_type.value,
            },
        )

        return entry

    async def create_double_entry(
        self,
        transaction_id: str,
        debit_account: AccountType,
        credit_account: AccountType,
        amount: Decimal,
        debit_balance_after: Decimal,
        credit_balance_after: Decimal,
        description: str | None = None,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        """
        Create a pair of ledger entries following double-entry bookkeeping.

        Args:
            transaction_id: Transaction ID
            debit_account: Debit account type
            credit_account: Credit account type
            amount: Transaction amount (must be positive)
            debit_balance_after: Balance after debit entry
            credit_balance_after: Balance after credit entry
            description: Optional description

        Returns:
            Tuple of (debit_entry, credit_entry)

        Raises:
            ValueError: If amount is not positive
        """
        logger.info(
            "Creating double-entry ledger entries",
            extra={
                "transaction_id": transaction_id,
                "debit_account": debit_account.value,
                "credit_account": credit_account.value,
                "amount": str(amount),
            },
        )

        # Create debit entry
        debit_entry = await self.create_debit_entry(
            transaction_id=transaction_id,
            account_type=debit_account,
            amount=amount,
            balance_after=debit_balance_after,
            description=description,
        )

        # Create credit entry
        credit_entry = await self.create_credit_entry(
            transaction_id=transaction_id,
            account_type=credit_account,
            amount=amount,
            balance_after=credit_balance_after,
            description=description,
        )

        logger.info(
            "Double-entry ledger entries created successfully",
            extra={
                "transaction_id": transaction_id,
                "debit_entry_id": debit_entry.id,
                "credit_entry_id": credit_entry.id,
            },
        )

        return debit_entry, credit_entry

    async def get_transaction_entries(self, transaction_id: str) -> list[LedgerEntry]:
        """
        Get all ledger entries for a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            List of ledger entries
        """
        logger.debug(
            "Fetching ledger entries for transaction",
            extra={"transaction_id": transaction_id},
        )

        query = (
            select(LedgerEntry)
            .where(LedgerEntry.transaction_id == transaction_id)
            .order_by(LedgerEntry.created_at)
        )
        result = await self.session.execute(query)
        entries = result.scalars().all()

        logger.debug(
            "Ledger entries retrieved",
            extra={
                "transaction_id": transaction_id,
                "entries_count": len(entries),
            },
        )

        return list(entries)

    async def get_account_entries(
        self,
        account_type: AccountType,
        limit: int = 100,
    ) -> list[LedgerEntry]:
        """
        Get ledger entries for a specific account type.

        Args:
            account_type: Account type
            limit: Maximum number of entries to return

        Returns:
            List of ledger entries
        """
        logger.debug(
            "Fetching ledger entries for account type",
            extra={"account_type": account_type.value, "limit": limit},
        )

        query = (
            select(LedgerEntry)
            .where(LedgerEntry.account_type == account_type.value)
            .order_by(desc(LedgerEntry.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        entries = result.scalars().all()

        logger.debug(
            "Ledger entries retrieved for account type",
            extra={
                "account_type": account_type.value,
                "entries_count": len(entries),
            },
        )

        return list(entries)

    async def calculate_account_balance(self, account_type: AccountType) -> Decimal:
        """
        Calculate the current balance for an account type.

        For asset and expense accounts: sum(debits) - sum(credits)
        For liability, equity, and revenue accounts: sum(credits) - sum(debits)

        Args:
            account_type: Account type

        Returns:
            Current account balance
        """
        logger.debug(
            "Calculating account balance",
            extra={"account_type": account_type.value},
        )

        entries = await self.get_account_entries(account_type, limit=10000)

        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)

        # Calculate balance based on account type
        if account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            balance = total_debits - total_credits
        else:  # LIABILITY, EQUITY, REVENUE
            balance = total_credits - total_debits

        logger.debug(
            "Account balance calculated",
            extra={
                "account_type": account_type.value,
                "total_debits": str(total_debits),
                "total_credits": str(total_credits),
                "balance": str(balance),
            },
        )

        return balance

    async def verify_double_entry_balance(self, transaction_id: str) -> bool:
        """
        Verify that ledger entries for a transaction are balanced.

        In double-entry bookkeeping, sum of debits must equal sum of credits.

        Args:
            transaction_id: Transaction ID

        Returns:
            True if balanced, False otherwise
        """
        logger.debug(
            "Verifying double-entry balance",
            extra={"transaction_id": transaction_id},
        )

        entries = await self.get_transaction_entries(transaction_id)

        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)

        is_balanced = total_debits == total_credits

        logger.info(
            "Double-entry balance verification",
            extra={
                "transaction_id": transaction_id,
                "total_debits": str(total_debits),
                "total_credits": str(total_credits),
                "is_balanced": is_balanced,
            },
        )

        return is_balanced

    async def get_audit_trail(
        self,
        transaction_id: str | None = None,
        account_type: AccountType | None = None,
        limit: int = 100,
    ) -> list[LedgerEntry]:
        """
        Get audit trail of ledger entries with optional filters.

        Args:
            transaction_id: Optional transaction ID filter
            account_type: Optional account type filter
            limit: Maximum number of entries to return

        Returns:
            List of ledger entries ordered by creation time
        """
        logger.debug(
            "Fetching audit trail",
            extra={
                "transaction_id": transaction_id,
                "account_type": account_type.value if account_type else None,
                "limit": limit,
            },
        )

        conditions = []
        if transaction_id:
            conditions.append(LedgerEntry.transaction_id == transaction_id)
        if account_type:
            conditions.append(LedgerEntry.account_type == account_type.value)

        query = select(LedgerEntry)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(LedgerEntry.created_at)).limit(limit)
        result = await self.session.execute(query)
        entries = result.scalars().all()

        logger.debug(
            "Audit trail retrieved",
            extra={"entries_count": len(entries)},
        )

        return list(entries)
