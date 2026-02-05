"""
Tests for Payment Event Handlers.

Comprehensive tests for payment event handling including task completion,
verification, rejection, and dispute events with various scenarios.
"""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.events.handlers import PaymentEventHandler
from src.payment_service.schemas.escrow import EscrowResponse

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_session():
    """Fixture for mocked database session."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_escrow_service():
    """Fixture for mocked escrow service."""
    with patch("src.payment_service.events.handlers.EscrowService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


class TestPaymentEventHandler:
    """Tests for PaymentEventHandler class."""

    @pytest.mark.asyncio
    async def test_handle_task_completed_event(self, mock_session, mock_escrow_service):
        """Test handling task completed event."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "worker_id": "user_worker",
        }

        escrow_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="held",
            transaction_id="txn_123",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=escrow_response)

        # Act
        await handler.handle_event("task.completed", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_task_completed_no_escrow(self, mock_session, mock_escrow_service):
        """Test handling task completed event with no escrow."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "worker_id": "user_worker",
        }

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=None)

        # Act
        await handler.handle_event("task.completed", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_task_verified_event(self, mock_session, mock_escrow_service):
        """Test handling task verified event."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
            "payee_wallet_id": "wallet_payee",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        release_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="released",
            transaction_id="txn_456",
        )

        mock_escrow_service.release_funds = AsyncMock(return_value=release_response)

        # Act
        await handler.handle_event("task.verified", event_data)

        # Assert
        mock_escrow_service.release_funds.assert_called_once()
        call_args = mock_escrow_service.release_funds.call_args[0][0]
        assert call_args.task_id == "task_123"
        assert call_args.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_handle_task_verified_missing_fields(self, mock_session, mock_escrow_service):
        """Test handling task verified event with missing fields."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
            # Missing payee_wallet_id and amount
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            await handler.handle_event("task.verified", event_data)

    @pytest.mark.asyncio
    async def test_handle_task_verified_release_failure(self, mock_session, mock_escrow_service):
        """Test handling task verified event when release fails."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
            "payee_wallet_id": "wallet_payee",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        mock_escrow_service.release_funds = AsyncMock(
            side_effect=ValueError("Insufficient escrow balance")
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to release escrow funds"):
            await handler.handle_event("task.verified", event_data)

    @pytest.mark.asyncio
    async def test_handle_task_rejected_event(self, mock_session, mock_escrow_service):
        """Test handling task rejected event."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
        }

        escrow_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="held",
            transaction_id="txn_123",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=escrow_response)

        with patch(
            "src.payment_service.events.handlers.WalletService"
        ) as mock_wallet_service_class:
            mock_wallet_service = MagicMock()
            mock_wallet_service.release_from_escrow = AsyncMock()
            mock_wallet_service_class.return_value = mock_wallet_service

            # Act
            await handler.handle_event("task.rejected", event_data)

            # Assert
            mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")
            mock_wallet_service.release_from_escrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_task_rejected_no_escrow(self, mock_session, mock_escrow_service):
        """Test handling task rejected event with no escrow."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
        }

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=None)

        # Act
        await handler.handle_event("task.rejected", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_task_rejected_already_released(
        self, mock_session, mock_escrow_service
    ):
        """Test handling task rejected event with already released escrow."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
        }

        escrow_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="released",
            transaction_id="txn_123",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=escrow_response)

        # Act
        await handler.handle_event("task.rejected", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_task_disputed_event(self, mock_session, mock_escrow_service):
        """Test handling task disputed event."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "dispute_id": "dispute_456",
            "dispute_reason": "Quality issues",
        }

        escrow_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="held",
            transaction_id="txn_123",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=escrow_response)

        # Act
        await handler.handle_event("task.disputed", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_task_disputed_no_escrow(self, mock_session, mock_escrow_service):
        """Test handling task disputed event with no escrow."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "dispute_id": "dispute_456",
            "dispute_reason": "Quality issues",
        }

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=None)

        # Act
        await handler.handle_event("task.disputed", event_data)

        # Assert
        mock_escrow_service.get_escrow_status.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self, mock_session, mock_escrow_service):
        """Test handling unknown event type."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {"task_id": "task_123"}

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown event type"):
            await handler.handle_event("task.unknown", event_data)

    @pytest.mark.asyncio
    async def test_handle_task_verified_with_custom_fee(self, mock_session, mock_escrow_service):
        """Test handling task verified event with custom platform fee."""
        # Arrange
        handler = PaymentEventHandler(mock_session)
        handler.escrow_service = mock_escrow_service

        event_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_payer",
            "payee_wallet_id": "wallet_payee",
            "amount": 200.00,
            "platform_fee_percentage": 0.10,
        }

        release_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_payer",
            payee_wallet_id="wallet_payee",
            amount=Decimal("200.00"),
            platform_fee=Decimal("20.00"),
            total_amount=Decimal("220.00"),
            status="released",
            transaction_id="txn_789",
        )

        mock_escrow_service.release_funds = AsyncMock(return_value=release_response)

        # Act
        await handler.handle_event("task.verified", event_data)

        # Assert
        mock_escrow_service.release_funds.assert_called_once()
        call_args = mock_escrow_service.release_funds.call_args[0][0]
        assert call_args.platform_fee_percentage == Decimal("0.10")
