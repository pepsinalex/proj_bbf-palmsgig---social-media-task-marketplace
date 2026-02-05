"""
Tests for Escrow Router.

Comprehensive tests for escrow endpoints including hold, release,
and status check operations with various scenarios.
"""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.payment_service.main import app
from src.payment_service.schemas.escrow import EscrowResponse

logger = logging.getLogger(__name__)

client = TestClient(app)


@pytest.fixture
def mock_escrow_service():
    """Fixture for mocked escrow service."""
    with patch("src.payment_service.routers.escrow.get_escrow_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


class TestHoldFundsEndpoint:
    """Tests for POST /api/v1/escrow/hold endpoint."""

    def test_hold_funds_success(self, mock_escrow_service):
        """Test successful escrow hold."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        expected_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_abc",
            payee_wallet_id="wallet_xyz",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="held",
            transaction_id="txn_123",
        )

        mock_escrow_service.hold_funds = AsyncMock(return_value=expected_response)

        # Act
        response = client.post("/api/v1/escrow/hold", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["status"] == "held"
        assert float(data["total_amount"]) == 105.00
        mock_escrow_service.hold_funds.assert_called_once()

    def test_hold_funds_insufficient_balance(self, mock_escrow_service):
        """Test escrow hold with insufficient balance."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        mock_escrow_service.hold_funds = AsyncMock(
            side_effect=ValueError("Insufficient balance for escrow hold")
        )

        # Act
        response = client.post("/api/v1/escrow/hold", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient balance" in response.json()["detail"]

    def test_hold_funds_invalid_amount(self, mock_escrow_service):
        """Test escrow hold with invalid amount."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": -50.00,
            "platform_fee_percentage": 0.05,
        }

        # Act
        response = client.post("/api/v1/escrow/hold", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_hold_funds_wallet_not_found(self, mock_escrow_service):
        """Test escrow hold with non-existent wallet."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_nonexistent",
            "payee_wallet_id": "wallet_xyz",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        mock_escrow_service.hold_funds = AsyncMock(
            side_effect=ValueError("Payer wallet not found: wallet_nonexistent")
        )

        # Act
        response = client.post("/api/v1/escrow/hold", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Payer wallet not found" in response.json()["detail"]


class TestReleaseFundsEndpoint:
    """Tests for POST /api/v1/escrow/release endpoint."""

    def test_release_funds_success(self, mock_escrow_service):
        """Test successful escrow release."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        expected_response = EscrowResponse(
            task_id="task_123",
            payer_wallet_id="wallet_abc",
            payee_wallet_id="wallet_xyz",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="released",
            transaction_id="txn_456",
        )

        mock_escrow_service.release_funds = AsyncMock(return_value=expected_response)

        # Act
        response = client.post("/api/v1/escrow/release", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["status"] == "released"
        assert float(data["amount"]) == 100.00
        mock_escrow_service.release_funds.assert_called_once()

    def test_release_funds_insufficient_escrow(self, mock_escrow_service):
        """Test escrow release with insufficient escrow balance."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": 100.00,
            "platform_fee_percentage": 0.05,
        }

        mock_escrow_service.release_funds = AsyncMock(
            side_effect=ValueError("Insufficient escrow balance")
        )

        # Act
        response = client.post("/api/v1/escrow/release", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient escrow balance" in response.json()["detail"]

    def test_release_funds_invalid_amount(self, mock_escrow_service):
        """Test escrow release with invalid amount."""
        # Arrange
        request_data = {
            "task_id": "task_123",
            "payer_wallet_id": "wallet_abc",
            "payee_wallet_id": "wallet_xyz",
            "amount": 0,
            "platform_fee_percentage": 0.05,
        }

        # Act
        response = client.post("/api/v1/escrow/release", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetEscrowStatusEndpoint:
    """Tests for GET /api/v1/escrow/{task_id} endpoint."""

    def test_get_escrow_status_success(self, mock_escrow_service):
        """Test successful escrow status retrieval."""
        # Arrange
        task_id = "task_123"
        expected_response = EscrowResponse(
            task_id=task_id,
            payer_wallet_id="wallet_abc",
            payee_wallet_id="wallet_xyz",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="held",
            transaction_id="txn_123",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=expected_response)

        # Act
        response = client.get(f"/api/v1/escrow/{task_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "held"
        mock_escrow_service.get_escrow_status.assert_called_once_with(task_id)

    def test_get_escrow_status_not_found(self, mock_escrow_service):
        """Test escrow status retrieval for non-existent task."""
        # Arrange
        task_id = "task_nonexistent"
        mock_escrow_service.get_escrow_status = AsyncMock(return_value=None)

        # Act
        response = client.get(f"/api/v1/escrow/{task_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Escrow not found" in response.json()["detail"]

    def test_get_escrow_status_released(self, mock_escrow_service):
        """Test escrow status retrieval for released escrow."""
        # Arrange
        task_id = "task_456"
        expected_response = EscrowResponse(
            task_id=task_id,
            payer_wallet_id="wallet_abc",
            payee_wallet_id="wallet_xyz",
            amount=Decimal("100.00"),
            platform_fee=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="released",
            transaction_id="txn_456",
        )

        mock_escrow_service.get_escrow_status = AsyncMock(return_value=expected_response)

        # Act
        response = client.get(f"/api/v1/escrow/{task_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "released"
