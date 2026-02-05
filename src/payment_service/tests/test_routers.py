"""
Tests for Payment Service API Routers.

Comprehensive tests for wallet and transaction API endpoints including
authentication, authorization, validation, and error handling.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from src.payment_service.main import app
from src.payment_service.models.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
from src.payment_service.models.wallet import Currency, Wallet, WalletStatus
from src.payment_service.services.transaction_service import TransactionService
from src.payment_service.services.wallet_service import WalletService


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_wallet_service() -> AsyncMock:
    """Create mock WalletService."""
    return AsyncMock(spec=WalletService)


@pytest.fixture
def mock_transaction_service() -> AsyncMock:
    """Create mock TransactionService."""
    return AsyncMock(spec=TransactionService)


@pytest.fixture
def sample_wallet() -> Wallet:
    """Create sample wallet."""
    wallet = Wallet(
        user_id="user-123",
        balance=Decimal("1000.0000"),
        escrow_balance=Decimal("50.0000"),
        currency=Currency.USD.value,
        status=WalletStatus.ACTIVE.value,
    )
    wallet.id = "wallet-123"
    return wallet


@pytest.fixture
def sample_transaction() -> Transaction:
    """Create sample transaction."""
    transaction = Transaction(
        wallet_id="wallet-123",
        type=TransactionType.DEPOSIT.value,
        amount=Decimal("100.0000"),
        currency="USD",
        status=TransactionStatus.COMPLETED.value,
        reference="TXN-20240115-123456",
        description="Test deposit",
    )
    transaction.id = "txn-123"
    return transaction


class TestCreateWalletEndpoint:
    """Tests for POST /wallets endpoint."""

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_create_wallet_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_wallet: Wallet,
    ) -> None:
        """Test successful wallet creation."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_wallet.return_value = sample_wallet
        mock_get_service.return_value = mock_service

        wallet_data = {
            "user_id": "user-123",
            "currency": "USD",
            "initial_balance": 1000.0000,
        }

        response = client.post("/api/v1/wallets", json=wallet_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["balance"] == "1000.0000"
        assert data["currency"] == "USD"

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    async def test_create_wallet_validation_error(
        self, mock_get_user: MagicMock, client: TestClient
    ) -> None:
        """Test wallet creation with invalid data."""
        mock_get_user.return_value = "user-123"

        wallet_data = {
            "user_id": "invalid-id",  # Not a valid UUID
            "currency": "INVALID",
        }

        response = client.post("/api/v1/wallets", json=wallet_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_create_wallet_duplicate_user(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test wallet creation for existing user."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_wallet.side_effect = ValueError("Wallet already exists")
        mock_get_service.return_value = mock_service

        wallet_data = {
            "user_id": "user-123",
            "currency": "USD",
        }

        response = client.post("/api/v1/wallets", json=wallet_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetWalletEndpoint:
    """Tests for GET /wallets/{wallet_id} endpoint."""

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_get_wallet_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_wallet: Wallet,
    ) -> None:
        """Test successful wallet retrieval."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_wallet.return_value = sample_wallet
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/wallets/wallet-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "wallet-123"
        assert data["balance"] == "1000.0000"

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_get_wallet_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test wallet retrieval when not found."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_wallet.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/wallets/nonexistent-123")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAddBalanceEndpoint:
    """Tests for POST /wallets/{wallet_id}/add-balance endpoint."""

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_add_balance_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_wallet: Wallet,
    ) -> None:
        """Test successful balance addition."""
        mock_get_user.return_value = "user-123"
        sample_wallet.balance = Decimal("1500.0000")
        mock_service = AsyncMock()
        mock_service.add_balance.return_value = sample_wallet
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/wallets/wallet-123/add-balance?amount=500.0000"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["balance"] == "1500.0000"

    @patch("src.payment_service.routers.wallet.get_current_user_id")
    @patch("src.payment_service.routers.wallet.get_wallet_service")
    async def test_add_balance_invalid_amount(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test adding negative balance."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.add_balance.side_effect = ValueError("Amount must be positive")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/wallets/wallet-123/add-balance?amount=-100.0000"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCreateTransactionEndpoint:
    """Tests for POST /transactions endpoint."""

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_create_transaction_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_transaction: Transaction,
    ) -> None:
        """Test successful transaction creation."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.create_transaction.return_value = sample_transaction
        mock_get_service.return_value = mock_service

        transaction_data = {
            "wallet_id": "wallet-123",
            "type": "deposit",
            "amount": 100.0000,
            "currency": "USD",
            "description": "Test deposit",
        }

        response = client.post("/api/v1/transactions", json=transaction_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["wallet_id"] == "wallet-123"
        assert data["type"] == "deposit"
        assert data["amount"] == "100.0000"

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    async def test_create_transaction_validation_error(
        self, mock_get_user: MagicMock, client: TestClient
    ) -> None:
        """Test transaction creation with invalid data."""
        mock_get_user.return_value = "user-123"

        transaction_data = {
            "wallet_id": "wallet-123",
            "type": "invalid_type",
            "amount": -100.0000,  # Negative amount
        }

        response = client.post("/api/v1/transactions", json=transaction_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetTransactionEndpoint:
    """Tests for GET /transactions/{transaction_id} endpoint."""

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_get_transaction_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_transaction: Transaction,
    ) -> None:
        """Test successful transaction retrieval."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_transaction.return_value = sample_transaction
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/transactions/txn-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "txn-123"
        assert data["status"] == "completed"

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_get_transaction_not_found(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test transaction retrieval when not found."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.get_transaction.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/transactions/nonexistent-123")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMarkTransactionAsCompletedEndpoint:
    """Tests for POST /transactions/{transaction_id}/mark-completed endpoint."""

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_mark_completed_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_transaction: Transaction,
    ) -> None:
        """Test successfully marking transaction as completed."""
        mock_get_user.return_value = "user-123"
        sample_transaction.status = TransactionStatus.COMPLETED.value
        mock_service = AsyncMock()
        mock_service.mark_as_completed.return_value = sample_transaction
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/transactions/txn-123/mark-completed?gateway_reference=GATEWAY-REF"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_mark_completed_invalid_status(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test marking completed with invalid status."""
        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        mock_service.mark_as_completed.side_effect = ValueError("Cannot mark as completed")
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/transactions/txn-123/mark-completed")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestListTransactionsEndpoint:
    """Tests for GET /transactions endpoint."""

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_list_transactions_success(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
        sample_transaction: Transaction,
    ) -> None:
        """Test successful transaction listing."""
        from src.payment_service.schemas.transaction import TransactionList, TransactionResponse

        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        
        transaction_response = TransactionResponse.model_validate(sample_transaction)
        transaction_list = TransactionList(
            transactions=[transaction_response],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )
        mock_service.list_transactions.return_value = transaction_list
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/transactions?page=1&page_size=20")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["transactions"]) == 1

    @patch("src.payment_service.routers.transaction.get_current_user_id")
    @patch("src.payment_service.routers.transaction.get_transaction_service")
    async def test_list_transactions_with_filters(
        self,
        mock_get_service: MagicMock,
        mock_get_user: MagicMock,
        client: TestClient,
    ) -> None:
        """Test transaction listing with filters."""
        from src.payment_service.schemas.transaction import TransactionList

        mock_get_user.return_value = "user-123"
        mock_service = AsyncMock()
        
        transaction_list = TransactionList(
            transactions=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        mock_service.list_transactions.return_value = transaction_list
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/transactions?wallet_id=wallet-123&status=completed&page=1"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
