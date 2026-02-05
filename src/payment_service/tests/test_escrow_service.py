"""
Tests for Escrow Service.

Comprehensive tests for escrow service including hold, release,
and status operations with various scenarios and edge cases.
"""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.transaction import Transaction, TransactionStatus, TransactionType
from src.payment_service.models.wallet import Currency, Wallet, WalletStatus
from src.payment_service.schemas.escrow import (
    EscrowHoldRequest,
    EscrowReleaseRequest,
)
from src.payment_service.services.escrow_service import EscrowService

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_session():
    """Fixture for mocked database session."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_wallet_service():
    """Fixture for mocked wallet service."""
    with patch("src.payment_service.services.escrow_service.WalletService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def sample_payer_wallet():
    """Fixture for sample payer wallet."""
    return Wallet(
        id="wallet_payer_123",
        user_id="user_payer",
        balance=Decimal("500.00"),
        escrow_balance=Decimal("0.00"),
        currency=Currency.USD.value,
        status=WalletStatus.ACTIVE.value,
    )


@pytest.fixture
def sample_payee_wallet():
    """Fixture for sample payee wallet."""
    return Wallet(
        id="wallet_payee_456",
        user_id="user_payee",
        balance=Decimal("100.00"),
        escrow_balance=Decimal("0.00"),
        currency=Currency.USD.value,
        status=WalletStatus.ACTIVE.value,
    )


class TestEscrowServiceHoldFunds:
    """Tests for EscrowService.hold_funds method."""

    @pytest.mark.asyncio
    async def test_hold_funds_success(
        self, mock_session, mock_wallet_service, sample_payer_wallet
    ):
        """Test successful escrow hold."""
        # Arrange
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowHoldRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(return_value=sample_payer_wallet)
        mock_wallet_service.move_to_escrow = AsyncMock(return_value=sample_payer_wallet)

        # Act
        result = await escrow_service.hold_funds(request)

        # Assert
        assert result.task_id == "task_123"
        assert result.amount == Decimal("100.00")
        assert result.platform_fee == Decimal("5.00")
        assert result.total_amount == Decimal("105.00")
        assert result.status == "held"
        mock_wallet_service.get_wallet.assert_called_once_with("wallet_payer_123")
        mock_wallet_service.move_to_escrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_hold_funds_wallet_not_found(self, mock_session, mock_wallet_service):
        """Test escrow hold with non-existent wallet."""
        # Arrange
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowHoldRequest(
            task_id="task_123",
            payer_wallet_id="wallet_nonexistent",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Payer wallet not found"):
            await escrow_service.hold_funds(request)

    @pytest.mark.asyncio
    async def test_hold_funds_insufficient_balance(
        self, mock_session, mock_wallet_service, sample_payer_wallet
    ):
        """Test escrow hold with insufficient balance."""
        # Arrange
        sample_payer_wallet.balance = Decimal("50.00")
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowHoldRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(return_value=sample_payer_wallet)

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient balance"):
            await escrow_service.hold_funds(request)

    @pytest.mark.asyncio
    async def test_hold_funds_inactive_wallet(
        self, mock_session, mock_wallet_service, sample_payer_wallet
    ):
        """Test escrow hold with inactive wallet."""
        # Arrange
        sample_payer_wallet.status = WalletStatus.SUSPENDED.value
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowHoldRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(return_value=sample_payer_wallet)

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient balance"):
            await escrow_service.hold_funds(request)


class TestEscrowServiceReleaseFunds:
    """Tests for EscrowService.release_funds method."""

    @pytest.mark.asyncio
    async def test_release_funds_success(
        self, mock_session, mock_wallet_service, sample_payer_wallet, sample_payee_wallet
    ):
        """Test successful escrow release."""
        # Arrange
        sample_payer_wallet.escrow_balance = Decimal("105.00")
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowReleaseRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(
            side_effect=[sample_payer_wallet, sample_payee_wallet]
        )
        mock_wallet_service.release_from_escrow = AsyncMock(return_value=sample_payer_wallet)
        mock_wallet_service.deduct_balance = AsyncMock(return_value=sample_payer_wallet)
        mock_wallet_service.add_balance = AsyncMock(return_value=sample_payee_wallet)

        # Act
        result = await escrow_service.release_funds(request)

        # Assert
        assert result.task_id == "task_123"
        assert result.amount == Decimal("100.00")
        assert result.platform_fee == Decimal("5.00")
        assert result.total_amount == Decimal("105.00")
        assert result.status == "released"
        assert mock_wallet_service.get_wallet.call_count == 2
        mock_wallet_service.release_from_escrow.assert_called_once()
        mock_wallet_service.deduct_balance.assert_called_once()
        mock_wallet_service.add_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_funds_payer_not_found(self, mock_session, mock_wallet_service):
        """Test escrow release with non-existent payer wallet."""
        # Arrange
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowReleaseRequest(
            task_id="task_123",
            payer_wallet_id="wallet_nonexistent",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="Payer wallet not found"):
            await escrow_service.release_funds(request)

    @pytest.mark.asyncio
    async def test_release_funds_payee_not_found(
        self, mock_session, mock_wallet_service, sample_payer_wallet
    ):
        """Test escrow release with non-existent payee wallet."""
        # Arrange
        sample_payer_wallet.escrow_balance = Decimal("105.00")
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowReleaseRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_nonexistent",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(side_effect=[sample_payer_wallet, None])

        # Act & Assert
        with pytest.raises(ValueError, match="Payee wallet not found"):
            await escrow_service.release_funds(request)

    @pytest.mark.asyncio
    async def test_release_funds_insufficient_escrow(
        self, mock_session, mock_wallet_service, sample_payer_wallet, sample_payee_wallet
    ):
        """Test escrow release with insufficient escrow balance."""
        # Arrange
        sample_payer_wallet.escrow_balance = Decimal("50.00")
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowReleaseRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(
            side_effect=[sample_payer_wallet, sample_payee_wallet]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient escrow balance"):
            await escrow_service.release_funds(request)

    @pytest.mark.asyncio
    async def test_release_funds_rollback_on_deduct_failure(
        self, mock_session, mock_wallet_service, sample_payer_wallet, sample_payee_wallet
    ):
        """Test escrow release rollback when deduction fails."""
        # Arrange
        sample_payer_wallet.escrow_balance = Decimal("105.00")
        escrow_service = EscrowService(mock_session)
        escrow_service.wallet_service = mock_wallet_service

        request = EscrowReleaseRequest(
            task_id="task_123",
            payer_wallet_id="wallet_payer_123",
            payee_wallet_id="wallet_payee_456",
            amount=Decimal("100.00"),
            platform_fee_percentage=Decimal("0.05"),
        )

        mock_wallet_service.get_wallet = AsyncMock(
            side_effect=[sample_payer_wallet, sample_payee_wallet]
        )
        mock_wallet_service.release_from_escrow = AsyncMock(return_value=sample_payer_wallet)
        mock_wallet_service.deduct_balance = AsyncMock(
            side_effect=ValueError("Deduction failed")
        )
        mock_wallet_service.move_to_escrow = AsyncMock(return_value=sample_payer_wallet)

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to process payment"):
            await escrow_service.release_funds(request)

        # Verify rollback was called
        mock_wallet_service.move_to_escrow.assert_called_once()


class TestEscrowServiceGetStatus:
    """Tests for EscrowService.get_escrow_status method."""

    @pytest.mark.asyncio
    async def test_get_escrow_status_found(self, mock_session):
        """Test getting escrow status for existing task."""
        # Arrange
        escrow_service = EscrowService(mock_session)
        task_id = "task_123"

        transaction = Transaction(
            id="txn_123",
            wallet_id="wallet_payer_123",
            type=TransactionType.PAYMENT.value,
            amount=Decimal("105.00"),
            currency=Currency.USD.value,
            status=TransactionStatus.PENDING.value,
            reference="REF_123",
            description="Escrow hold",
            metadata={
                "task_id": task_id,
                "payee_wallet_id": "wallet_payee_456",
                "base_amount": "100.00",
                "platform_fee": "5.00",
            },
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=transaction)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await escrow_service.get_escrow_status(task_id)

        # Assert
        assert result is not None
        assert result.task_id == task_id
        assert result.status == "held"
        assert result.transaction_id == "txn_123"

    @pytest.mark.asyncio
    async def test_get_escrow_status_not_found(self, mock_session):
        """Test getting escrow status for non-existent task."""
        # Arrange
        escrow_service = EscrowService(mock_session)
        task_id = "task_nonexistent"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await escrow_service.get_escrow_status(task_id)

        # Assert
        assert result is None
