"""
Tests for Payment Service Models.

Comprehensive tests for Wallet, Transaction, and LedgerEntry models
including validation, relationships, and business logic.
"""

import pytest
from decimal import Decimal

from src.payment_service.models.ledger_entry import AccountType, LedgerEntry
from src.payment_service.models.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
from src.payment_service.models.wallet import Currency, Wallet, WalletStatus


class TestWalletModel:
    """Tests for Wallet model."""

    def test_create_wallet(self) -> None:
        """Test creating a wallet instance."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("50.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        assert wallet.user_id == "user-123"
        assert wallet.balance == Decimal("1000.0000")
        assert wallet.escrow_balance == Decimal("50.0000")
        assert wallet.currency == Currency.USD.value
        assert wallet.status == WalletStatus.ACTIVE.value

    def test_get_total_balance(self) -> None:
        """Test get_total_balance method."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("50.0000"),
            currency=Currency.USD.value,
        )

        total = wallet.get_total_balance()
        assert total == Decimal("1050.0000")

    def test_can_transact_active_wallet(self) -> None:
        """Test can_transact with active wallet and sufficient balance."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        assert wallet.can_transact(Decimal("500.0000")) is True
        assert wallet.can_transact(Decimal("1000.0000")) is True
        assert wallet.can_transact(Decimal("1500.0000")) is False

    def test_can_transact_inactive_wallet(self) -> None:
        """Test can_transact with suspended wallet."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.SUSPENDED.value,
        )

        assert wallet.can_transact(Decimal("100.0000")) is False

    def test_can_transact_negative_amount(self) -> None:
        """Test can_transact with negative amount."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
            status=WalletStatus.ACTIVE.value,
        )

        assert wallet.can_transact(Decimal("-100.0000")) is False

    def test_move_to_escrow_success(self) -> None:
        """Test moving funds to escrow successfully."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
        )

        wallet.move_to_escrow(Decimal("300.0000"))

        assert wallet.balance == Decimal("700.0000")
        assert wallet.escrow_balance == Decimal("300.0000")

    def test_move_to_escrow_insufficient_balance(self) -> None:
        """Test moving to escrow with insufficient balance."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("100.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
        )

        with pytest.raises(ValueError, match="Insufficient balance"):
            wallet.move_to_escrow(Decimal("200.0000"))

    def test_move_to_escrow_invalid_amount(self) -> None:
        """Test moving to escrow with invalid amount."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("0.0000"),
            currency=Currency.USD.value,
        )

        with pytest.raises(ValueError, match="Amount must be positive"):
            wallet.move_to_escrow(Decimal("0.0000"))

        with pytest.raises(ValueError, match="Amount must be positive"):
            wallet.move_to_escrow(Decimal("-100.0000"))

    def test_release_from_escrow_success(self) -> None:
        """Test releasing funds from escrow successfully."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("700.0000"),
            escrow_balance=Decimal("300.0000"),
            currency=Currency.USD.value,
        )

        wallet.release_from_escrow(Decimal("150.0000"))

        assert wallet.balance == Decimal("850.0000")
        assert wallet.escrow_balance == Decimal("150.0000")

    def test_release_from_escrow_insufficient_balance(self) -> None:
        """Test releasing from escrow with insufficient escrow balance."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("50.0000"),
            currency=Currency.USD.value,
        )

        with pytest.raises(ValueError, match="Insufficient escrow balance"):
            wallet.release_from_escrow(Decimal("100.0000"))

    def test_release_from_escrow_invalid_amount(self) -> None:
        """Test releasing from escrow with invalid amount."""
        wallet = Wallet(
            user_id="user-123",
            balance=Decimal("1000.0000"),
            escrow_balance=Decimal("300.0000"),
            currency=Currency.USD.value,
        )

        with pytest.raises(ValueError, match="Amount must be positive"):
            wallet.release_from_escrow(Decimal("0.0000"))


class TestTransactionModel:
    """Tests for Transaction model."""

    def test_create_transaction(self) -> None:
        """Test creating a transaction instance."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-20240115-123456",
        )

        assert transaction.wallet_id == "wallet-123"
        assert transaction.type == TransactionType.DEPOSIT.value
        assert transaction.amount == Decimal("100.0000")
        assert transaction.currency == "USD"
        assert transaction.status == TransactionStatus.PENDING.value
        assert transaction.reference == "TXN-20240115-123456"

    def test_is_pending(self) -> None:
        """Test is_pending method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-123",
        )

        assert transaction.is_pending() is True

        transaction.status = TransactionStatus.COMPLETED.value
        assert transaction.is_pending() is False

    def test_is_completed(self) -> None:
        """Test is_completed method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.COMPLETED.value,
            reference="TXN-123",
        )

        assert transaction.is_completed() is True

        transaction.status = TransactionStatus.PENDING.value
        assert transaction.is_completed() is False

    def test_is_failed(self) -> None:
        """Test is_failed method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.FAILED.value,
            reference="TXN-123",
        )

        assert transaction.is_failed() is True

        transaction.status = TransactionStatus.CANCELLED.value
        assert transaction.is_failed() is True

        transaction.status = TransactionStatus.COMPLETED.value
        assert transaction.is_failed() is False

    def test_mark_as_processing(self) -> None:
        """Test mark_as_processing method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-123",
        )

        transaction.mark_as_processing()
        assert transaction.status == TransactionStatus.PROCESSING.value

    def test_mark_as_processing_invalid_status(self) -> None:
        """Test mark_as_processing with invalid current status."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.COMPLETED.value,
            reference="TXN-123",
        )

        with pytest.raises(ValueError, match="Cannot mark as processing"):
            transaction.mark_as_processing()

    def test_mark_as_completed(self) -> None:
        """Test mark_as_completed method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PROCESSING.value,
            reference="TXN-123",
        )

        transaction.mark_as_completed("GATEWAY-REF-123")
        assert transaction.status == TransactionStatus.COMPLETED.value
        assert transaction.gateway_reference == "GATEWAY-REF-123"

    def test_mark_as_completed_invalid_status(self) -> None:
        """Test mark_as_completed with invalid current status."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.FAILED.value,
            reference="TXN-123",
        )

        with pytest.raises(ValueError, match="Cannot mark as completed"):
            transaction.mark_as_completed()

    def test_mark_as_failed(self) -> None:
        """Test mark_as_failed method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PROCESSING.value,
            reference="TXN-123",
        )

        transaction.mark_as_failed("Payment gateway error")
        assert transaction.status == TransactionStatus.FAILED.value
        assert transaction.metadata["error"] == "Payment gateway error"

    def test_mark_as_failed_completed_transaction(self) -> None:
        """Test mark_as_failed on completed transaction."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.COMPLETED.value,
            reference="TXN-123",
        )

        with pytest.raises(ValueError, match="Cannot mark completed transaction as failed"):
            transaction.mark_as_failed()

    def test_cancel_transaction(self) -> None:
        """Test cancel method."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PENDING.value,
            reference="TXN-123",
        )

        transaction.cancel()
        assert transaction.status == TransactionStatus.CANCELLED.value

    def test_cancel_transaction_invalid_status(self) -> None:
        """Test cancel with invalid current status."""
        transaction = Transaction(
            wallet_id="wallet-123",
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("100.0000"),
            currency="USD",
            status=TransactionStatus.PROCESSING.value,
            reference="TXN-123",
        )

        with pytest.raises(ValueError, match="Cannot cancel transaction"):
            transaction.cancel()


class TestLedgerEntryModel:
    """Tests for LedgerEntry model."""

    def test_create_debit_entry(self) -> None:
        """Test creating a debit ledger entry."""
        entry = LedgerEntry.create_debit_entry(
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
        assert entry.balance_after == Decimal("1100.0000")
        assert entry.description == "Test debit"

    def test_create_credit_entry(self) -> None:
        """Test creating a credit ledger entry."""
        entry = LedgerEntry.create_credit_entry(
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
        assert entry.balance_after == Decimal("500.0000")
        assert entry.description == "Test credit"

    def test_create_debit_entry_invalid_amount(self) -> None:
        """Test creating debit entry with invalid amount."""
        with pytest.raises(ValueError, match="Debit amount must be positive"):
            LedgerEntry.create_debit_entry(
                transaction_id="txn-123",
                account_type=AccountType.ASSET,
                amount=Decimal("0.0000"),
                balance_after=Decimal("1000.0000"),
            )

    def test_create_credit_entry_invalid_amount(self) -> None:
        """Test creating credit entry with invalid amount."""
        with pytest.raises(ValueError, match="Credit amount must be positive"):
            LedgerEntry.create_credit_entry(
                transaction_id="txn-123",
                account_type=AccountType.LIABILITY,
                amount=Decimal("-50.0000"),
                balance_after=Decimal("1000.0000"),
            )

    def test_is_debit(self) -> None:
        """Test is_debit method."""
        debit_entry = LedgerEntry.create_debit_entry(
            transaction_id="txn-123",
            account_type=AccountType.ASSET,
            amount=Decimal("100.0000"),
            balance_after=Decimal("1100.0000"),
        )

        assert debit_entry.is_debit() is True
        assert debit_entry.is_credit() is False

    def test_is_credit(self) -> None:
        """Test is_credit method."""
        credit_entry = LedgerEntry.create_credit_entry(
            transaction_id="txn-123",
            account_type=AccountType.LIABILITY,
            amount=Decimal("100.0000"),
            balance_after=Decimal("500.0000"),
        )

        assert credit_entry.is_credit() is True
        assert credit_entry.is_debit() is False

    def test_get_amount(self) -> None:
        """Test get_amount method."""
        debit_entry = LedgerEntry.create_debit_entry(
            transaction_id="txn-123",
            account_type=AccountType.ASSET,
            amount=Decimal("100.0000"),
            balance_after=Decimal("1100.0000"),
        )

        assert debit_entry.get_amount() == Decimal("100.0000")

        credit_entry = LedgerEntry.create_credit_entry(
            transaction_id="txn-123",
            account_type=AccountType.LIABILITY,
            amount=Decimal("200.0000"),
            balance_after=Decimal("500.0000"),
        )

        assert credit_entry.get_amount() == Decimal("200.0000")
