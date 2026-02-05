"""
Tests for Payment Service Services.

Comprehensive tests for WalletService, TransactionService, and LedgerService
including CRUD operations, balance management, and business logic.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.ledger_entry import AccountType, LedgerEntry
from src.payment_service.models.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
from src.payment_service.models.wallet import Currency, Wallet, WalletStatus
from src.payment_service.schemas.transaction import TransactionCreate
from src.payment_service.schemas.wallet import WalletCreate, WalletUpdate
from src.payment_service.services.ledger_service import LedgerService
from src.payment_service.services.transaction_service import TransactionService
from src.payment_service.services.wallet_service import WalletService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def wallet_service(mock_session: AsyncMock) -> WalletService:
    """Create WalletService instance with mock session."""
    return WalletService(mock_session)


@pytest.fixture
def transaction_service(mock_session: AsyncMock) -> TransactionService:
    """Create TransactionService instance with mock session."""
    return TransactionService(mock_session)


@pytest.fixture
def ledger_service(mock_session: AsyncMock) -> LedgerService:
    """Create LedgerService instance with mock session."""
    return LedgerService(mock_session)


@pytest.fixture
def sample_wallet_data() -> WalletCreate:
    """Create sample wallet creation data."""
    return WalletCreate(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        currency=Currency.USD,
        initial_balance=Decimal("1000.0000"),
    )


@pytest.fixture
def sample_transaction_data() -> TransactionCreate:
    """Create sample transaction creation data."""
    return TransactionCreate(
        wallet_id="550e8400-e29b-41d4-a716-446655440000",
        type=TransactionType.DEPOSIT,
        amount=Decimal("100.0000"),
        currency="USD",
        description="Test deposit",
    )


class TestWalletService:
    """Tests for WalletService."""

    async def test_create_wallet_success(
        self, wallet_service: WalletService, mock_session: AsyncMock, sample_wallet_data: WalletCreate
    ) -> None:
        """Test successful wallet creation."""
        # Mock get_wallet_by_user_id to return None (no existing wallet)
        wallet_service.get_wallet_by_user_id = AsyncMock(return_value=None)

        wallet = await wallet_service.create_wallet(sample_wallet_data)

        assert wallet.user_id == sample_wallet_data.user_id
        assert wallet.balance == sample_wallet_data.initial_balance
        assert wallet.escrow_balance == Decimal("0.0000")
        assert wallet.currency == sample_wallet_data.currency.value
        assert wallet.status == WalletStatus.ACTIVE.value

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_wallet_duplicate_user(
        self, wallet_service: WalletService, mock_session: AsyncMock, sample_wallet_data: WalletCreate
    ) -> None:
        """Test creating wallet for user who already has one."""
        existing_wallet = Wallet(
            user_id=sample_wallet_data.user_id,
            balance=Decimal("500.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet_by_user_id = AsyncMock(return_value=existing_wallet)

        with pytest.raises(ValueError, match="Wallet already exists"):
            await wallet_service.create_wallet(sample_wallet_data)

    async def test_get_wallet_found(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test getting an existing wallet."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("50.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_wallet
        mock_session.execute.return_value = mock_result

        wallet = await wallet_service.get_wallet(wallet_id)

        assert wallet is not None
        assert wallet.id == wallet_id
        assert wallet.balance == Decimal("1000.0000")

    async def test_add_balance_success(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test adding balance to wallet."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.add_balance(wallet_id, Decimal("500.0000"))

        assert wallet.balance == Decimal("1500.0000")
        mock_session.commit.assert_called_once()

    async def test_add_balance_invalid_amount(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test adding negative balance."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await wallet_service.add_balance("wallet-123", Decimal("-100.0000"))

    async def test_deduct_balance_success(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test deducting balance from wallet."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.deduct_balance(wallet_id, Decimal("300.0000"))

        assert wallet.balance == Decimal("700.0000")
        mock_session.commit.assert_called_once()

    async def test_deduct_balance_insufficient_funds(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test deducting more than available balance."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("100.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        with pytest.raises(ValueError, match="Insufficient balance"):
            await wallet_service.deduct_balance(wallet_id, Decimal("500.0000"))

    async def test_move_to_escrow_success(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test moving funds to escrow."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.move_to_escrow(wallet_id, Decimal("300.0000"))

        assert wallet.balance == Decimal("700.0000")
        assert wallet.escrow_balance == Decimal("300.0000")
        mock_session.commit.assert_called_once()

    async def test_release_from_escrow_success(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test releasing funds from escrow."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("700.0000"),
            escrow_balance=Decimal("300.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.release_from_escrow(wallet_id, Decimal("150.0000"))

        assert wallet.balance == Decimal("850.0000")
        assert wallet.escrow_balance == Decimal("150.0000")
        mock_session.commit.assert_called_once()

    async def test_suspend_wallet_success(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test suspending a wallet."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.suspend_wallet(wallet_id, "Suspicious activity")

        assert wallet.status == WalletStatus.SUSPENDED.value
        mock_session.commit.assert_called_once()

    async def test_close_wallet_with_zero_balance(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test closing wallet with zero balance."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("0.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        wallet = await wallet_service.close_wallet(wallet_id, "User request")

        assert wallet.status == WalletStatus.CLOSED.value
        mock_session.commit.assert_called_once()

    async def test_close_wallet_with_balance(
        self, wallet_service: WalletService, mock_session: AsyncMock
    ) -> None:
        """Test closing wallet with non-zero balance."""
        wallet_id = "wallet-123"
        mock_wallet = Wallet(
            id=wallet_id,
            user_id="user-123",
            balance=Decimal("100.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        wallet_service.get_wallet = AsyncMock(return_value=mock_wallet)

        with pytest.raises(ValueError, match="Cannot close wallet with non-zero balance"):
            await wallet_service.close_wallet(wallet_id)


class TestTransactionService:
    """Tests for TransactionService."""

    async def test_create_transaction_success(
        self,
        transaction_service: TransactionService,
        mock_session: AsyncMock,
        sample_transaction_data: TransactionCreate,
    ) -> None:
        """Test successful transaction creation."""
        # Mock get_transaction_by_reference to return None (no duplicate)
        transaction_service.get_transaction_by_reference = AsyncMock(return_value=None)

        transaction = await transaction_service.create_transaction(sample_transaction_data)

        assert transaction.wallet_id == sample_transaction_data.wallet_id
        assert transaction.type == sample_transaction_data.type.value
        assert transaction.amount == sample_transaction_data.amount
        assert transaction.currency == sample_transaction_data.currency
        assert transaction.status == TransactionStatus.PENDING.value

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_create_transaction_generates_reference(
        self,
        transaction_service: TransactionService,
        mock_session: AsyncMock,
        sample_transaction_data: TransactionCreate,
    ) -> None:
        """Test transaction reference generation."""
        sample_transaction_data.reference = None
        transaction_service.get_transaction_by_reference = AsyncMock(return_value=None)

        transaction = await transaction_service.create_transaction(sample_transaction_data)

        assert transaction.reference is not None
        assert transaction.reference.startswith("TXN-")

    async def test_mark_as_processing_success(
        self, transaction_service: TransactionService, mock_session: AsyncMock
    ) -> None:
        """Test marking transaction as processing."""
        transaction_id = "txn-123"
        mock_transaction = Transaction(
            id=transaction_id,
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-REF-123",
        )

        transaction_service.get_transaction = AsyncMock(return_value=mock_transaction)

        transaction = await transaction_service.mark_as_processing(transaction_id)

        assert transaction.status == TransactionStatus.PROCESSING.value
        mock_session.commit.assert_called_once()

    async def test_mark_as_completed_success(
        self, transaction_service: TransactionService, mock_session: AsyncMock
    ) -> None:
        """Test marking transaction as completed."""
        transaction_id = "txn-123"
        mock_transaction = Transaction(
            id=transaction_id,
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PROCESSING.value,
            reference="TXN-REF-123",
        )

        transaction_service.get_transaction = AsyncMock(return_value=mock_transaction)

        transaction = await transaction_service.mark_as_completed(
            transaction_id, "GATEWAY-REF-123"
        )

        assert transaction.status == TransactionStatus.COMPLETED.value
        assert transaction.gateway_reference == "GATEWAY-REF-123"
        mock_session.commit.assert_called_once()

    async def test_mark_as_failed_success(
        self, transaction_service: TransactionService, mock_session: AsyncMock
    ) -> None:
        """Test marking transaction as failed."""
        transaction_id = "txn-123"
        mock_transaction = Transaction(
            id=transaction_id,
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PROCESSING.value,
            reference="TXN-REF-123",
        )

        transaction_service.get_transaction = AsyncMock(return_value=mock_transaction)

        transaction = await transaction_service.mark_as_failed(
            transaction_id, "Payment gateway error"
        )

        assert transaction.status == TransactionStatus.FAILED.value
        assert transaction.metadata["error"] == "Payment gateway error"
        mock_session.commit.assert_called_once()

    async def test_cancel_transaction_success(
        self, transaction_service: TransactionService, mock_session: AsyncMock
    ) -> None:
        """Test cancelling a pending transaction."""
        transaction_id = "txn-123"
        mock_transaction = Transaction(
            id=transaction_id,
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-REF-123",
        )

        transaction_service.get_transaction = AsyncMock(return_value=mock_transaction)

        transaction = await transaction_service.cancel_transaction(transaction_id)

        assert transaction.status == TransactionStatus.CANCELLED.value
        mock_session.commit.assert_called_once()


class TestLedgerService:
    """Tests for LedgerService."""

    async def test_create_debit_entry_success(
        self, ledger_service: LedgerService, mock_session: AsyncMock
    ) -> None:
        """Test creating a debit ledger entry."""
        entry = await ledger_service.create_debit_entry(
            transaction_id="txn-123",
            account_type=AccountType.ASSET,
            amount=Decimal("100.0000"),
            balance_after=Decimal("1100.0000"),
            description="Test debit",
        )

        assert entry.transaction_id == "txn-123"
        assert entry.account_type == AccountType.ASSET.value
        assert entry.debit_amount == Decimal("100.0000")
        assert entry.credit_amount == Decimal("0.0000")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_create_credit_entry_success(
        self, ledger_service: LedgerService, mock_session: AsyncMock
    ) -> None:
        """Test creating a credit ledger entry."""
        entry = await ledger_service.create_credit_entry(
            transaction_id="txn-123",
            account_type=AccountType.LIABILITY,
            amount=Decimal("100.0000"),
            balance_after=Decimal("500.0000"),
            description="Test credit",
        )

        assert entry.transaction_id == "txn-123"
        assert entry.account_type == AccountType.LIABILITY.value
        assert entry.debit_amount == Decimal("0.0000")
        assert entry.credit_amount == Decimal("100.0000")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_create_double_entry_success(
        self, ledger_service: LedgerService, mock_session: AsyncMock
    ) -> None:
        """Test creating double-entry ledger entries."""
        debit_entry, credit_entry = await ledger_service.create_double_entry(
            transaction_id="txn-123",
            debit_account=AccountType.ASSET,
            credit_account=AccountType.LIABILITY,
            amount=Decimal("100.0000"),
            debit_balance_after=Decimal("1100.0000"),
            credit_balance_after=Decimal("500.0000"),
            description="Test double entry",
        )

        assert debit_entry.debit_amount == Decimal("100.0000")
        assert credit_entry.credit_amount == Decimal("100.0000")
        assert mock_session.add.call_count == 2
        assert mock_session.commit.call_count == 2

    async def test_verify_double_entry_balance_success(
        self, ledger_service: LedgerService, mock_session: AsyncMock
    ) -> None:
        """Test verifying balanced double-entry ledger entries."""
        debit_entry = LedgerEntry.create_debit_entry(
            transaction_id="txn-123",
            account_type=AccountType.ASSET,
            amount=Decimal("100.0000"),
            balance_after=Decimal("1100.0000"),
        )
        credit_entry = LedgerEntry.create_credit_entry(
            transaction_id="txn-123",
            account_type=AccountType.LIABILITY,
            amount=Decimal("100.0000"),
            balance_after=Decimal("500.0000"),
        )

        ledger_service.get_transaction_entries = AsyncMock(
            return_value=[debit_entry, credit_entry]
        )

        is_balanced = await ledger_service.verify_double_entry_balance("txn-123")

        assert is_balanced is True
