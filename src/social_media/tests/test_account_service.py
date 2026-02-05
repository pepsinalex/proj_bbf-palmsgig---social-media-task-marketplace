"""
Tests for Account Management Service.

Comprehensive tests for AccountService including account linking, verification,
unlinking, duplicate detection, token refresh, and error scenarios.
Mock database operations and external API calls.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.social_media.enums.platform_enums import Platform
from src.social_media.models.social_account import SocialAccount
from src.social_media.services.account_service import AccountService

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def account_service(mock_session: AsyncMock) -> AccountService:
    """Create AccountService instance with mock session."""
    return AccountService(mock_session)


@pytest.fixture
def sample_account() -> SocialAccount:
    """Create sample social account."""
    account = SocialAccount(
        id="account-123",
        user_id="user-123",
        platform=Platform.FACEBOOK.value,
        account_id="fb_account_123",
        username="johndoe",
        display_name="John Doe",
        access_token=SocialAccount.encrypt_token("test_access_token"),
        refresh_token=SocialAccount.encrypt_token("test_refresh_token"),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        scope="email profile",
        is_verified=False,
    )
    return account


@pytest.fixture
def mock_oauth_service() -> AsyncMock:
    """Create mock OAuth service."""
    service = AsyncMock()
    service.refresh_token = AsyncMock(
        return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "expires_at": datetime.utcnow() + timedelta(hours=1),
        }
    )
    service.close = AsyncMock()
    return service


class TestAccountServiceInitialization:
    """Tests for account service initialization."""

    def test_init_creates_oauth_service(
        self, account_service: AccountService
    ) -> None:
        """Test service initialization creates OAuth service."""
        assert account_service.oauth_service is not None
        assert account_service.db is not None

    @pytest.mark.asyncio
    async def test_close_closes_oauth_service(
        self, account_service: AccountService
    ) -> None:
        """Test close method closes OAuth service."""
        with patch.object(
            account_service.oauth_service, "close", new=AsyncMock()
        ) as mock_close:
            await account_service.close()
            mock_close.assert_called_once()


class TestAccountLinking:
    """Tests for account linking functionality."""

    @pytest.mark.asyncio
    async def test_link_account_success(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test successful account linking."""
        # Mock no existing account
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        expires_at = datetime.utcnow() + timedelta(hours=1)

        account = await account_service.link_account(
            user_id="user123",
            platform=Platform.FACEBOOK,
            account_id="fb_123",
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=expires_at,
            scope="email profile",
            username="johndoe",
            display_name="John Doe",
        )

        assert account.user_id == "user123"
        assert account.platform == Platform.FACEBOOK.value
        assert account.account_id == "fb_123"
        assert account.username == "johndoe"
        assert account.is_verified is False

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_account_encrypts_tokens(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test account linking encrypts tokens."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(
            SocialAccount, "encrypt_token", return_value="encrypted_token"
        ) as mock_encrypt:
            await account_service.link_account(
                user_id="user123",
                platform=Platform.FACEBOOK,
                account_id="fb_123",
                access_token="plain_token",
                refresh_token="plain_refresh",
            )

            assert mock_encrypt.call_count == 2  # access_token and refresh_token

    @pytest.mark.asyncio
    async def test_link_account_update_existing(
        self, account_service: AccountService, mock_session: AsyncMock, sample_account: SocialAccount
    ) -> None:
        """Test updating existing account link."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        new_expires = datetime.utcnow() + timedelta(hours=2)

        account = await account_service.link_account(
            user_id="user-123",
            platform=Platform.FACEBOOK,
            account_id="fb_account_123",
            access_token="new_token",
            refresh_token="new_refresh",
            expires_at=new_expires,
            username="johndoe_updated",
        )

        assert account == sample_account
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_account_duplicate_different_user(
        self, account_service: AccountService, mock_session: AsyncMock, sample_account: SocialAccount
    ) -> None:
        """Test linking fails when account belongs to different user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already linked to another user"):
            await account_service.link_account(
                user_id="different-user",
                platform=Platform.FACEBOOK,
                account_id="fb_account_123",
                access_token="test_token",
            )

    @pytest.mark.asyncio
    async def test_link_account_handles_db_error(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test account linking handles database errors."""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(ValueError, match="Failed to link account"):
            await account_service.link_account(
                user_id="user123",
                platform=Platform.FACEBOOK,
                account_id="fb_123",
                access_token="test_token",
            )

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_account_without_optional_fields(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test linking account with minimal required fields."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        account = await account_service.link_account(
            user_id="user123",
            platform=Platform.TWITTER,
            account_id="tw_123",
            access_token="test_token",
        )

        assert account.username is None
        assert account.display_name is None
        assert account.refresh_token is None


class TestAccountVerification:
    """Tests for account verification."""

    @pytest.mark.asyncio
    async def test_verify_account_success(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful account verification."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        # Mock platform client verification
        with patch(
            "src.social_media.services.account_service.FacebookClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.verify_account = AsyncMock(
                return_value={"id": "fb_account_123", "name": "John Doe"}
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await account_service.verify_account(
                account_id="account-123",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result is True
            assert sample_account.is_verified is True
            assert sample_account.last_verified_at is not None
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_account_not_found(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test verification fails when account not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Account not found"):
            await account_service.verify_account(
                account_id="nonexistent",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

    @pytest.mark.asyncio
    async def test_verify_account_platform_verification_fails(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test verification fails when platform verification fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        with patch(
            "src.social_media.services.account_service.FacebookClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.verify_account = AsyncMock(
                side_effect=ValueError("Invalid token")
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await account_service.verify_account(
                account_id="account-123",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            assert result is False
            assert sample_account.is_verified is False

    @pytest.mark.asyncio
    async def test_verify_account_expired_token(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test verification with expired token."""
        sample_account.expires_at = datetime.utcnow() - timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="expired"):
            await account_service.verify_account(
                account_id="account-123",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )


class TestAccountUnlinking:
    """Tests for account unlinking."""

    @pytest.mark.asyncio
    async def test_unlink_account_success(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test successful account unlinking."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        result = await account_service.unlink_account(
            user_id="user-123",
            account_id="account-123",
        )

        assert result is True
        mock_session.delete.assert_called_once_with(sample_account)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlink_account_not_found(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test unlinking non-existent account."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await account_service.unlink_account(
                user_id="user123",
                account_id="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_unlink_account_wrong_user(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test unlinking account owned by different user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not authorized"):
            await account_service.unlink_account(
                user_id="different-user",
                account_id="account-123",
            )

    @pytest.mark.asyncio
    async def test_unlink_account_handles_db_error(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test unlinking handles database errors."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result
        mock_session.delete.side_effect = Exception("Database error")

        with pytest.raises(ValueError, match="Failed to unlink"):
            await account_service.unlink_account(
                user_id="user-123",
                account_id="account-123",
            )

        mock_session.rollback.assert_called_once()


class TestTokenRefresh:
    """Tests for token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_account_tokens_success(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
        mock_oauth_service: AsyncMock,
    ) -> None:
        """Test successful token refresh."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        account_service.oauth_service = mock_oauth_service

        result = await account_service.refresh_account_tokens(
            account_id="account-123",
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert result is True
        mock_oauth_service.refresh_token.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_account_tokens_no_refresh_token(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test refresh fails when no refresh token available."""
        sample_account.refresh_token = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="No refresh token"):
            await account_service.refresh_account_tokens(
                account_id="account-123",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

    @pytest.mark.asyncio
    async def test_refresh_account_tokens_oauth_failure(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
        mock_oauth_service: AsyncMock,
    ) -> None:
        """Test token refresh handles OAuth service failures."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        mock_oauth_service.refresh_token.side_effect = ValueError("OAuth error")
        account_service.oauth_service = mock_oauth_service

        with pytest.raises(ValueError, match="Failed to refresh tokens"):
            await account_service.refresh_account_tokens(
                account_id="account-123",
                client_id="test_client_id",
                client_secret="test_client_secret",
            )


class TestAccountRetrieval:
    """Tests for account retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_user_accounts_success(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test getting all user accounts."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_account]
        mock_session.execute.return_value = mock_result

        accounts = await account_service.get_user_accounts(user_id="user-123")

        assert len(accounts) == 1
        assert accounts[0] == sample_account

    @pytest.mark.asyncio
    async def test_get_user_accounts_by_platform(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test getting user accounts filtered by platform."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_account]
        mock_session.execute.return_value = mock_result

        accounts = await account_service.get_user_accounts(
            user_id="user-123",
            platform=Platform.FACEBOOK,
        )

        assert len(accounts) == 1
        assert accounts[0].platform == Platform.FACEBOOK.value

    @pytest.mark.asyncio
    async def test_get_user_accounts_empty(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test getting accounts returns empty list when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        accounts = await account_service.get_user_accounts(user_id="user123")

        assert len(accounts) == 0

    @pytest.mark.asyncio
    async def test_get_account_by_id_success(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test getting account by ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        account = await account_service.get_account_by_id(
            account_id="account-123",
            user_id="user-123",
        )

        assert account == sample_account

    @pytest.mark.asyncio
    async def test_get_account_by_id_not_found(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test getting non-existent account returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        account = await account_service.get_account_by_id(
            account_id="nonexistent",
            user_id="user123",
        )

        assert account is None


class TestDuplicateDetection:
    """Tests for duplicate account detection."""

    @pytest.mark.asyncio
    async def test_check_duplicate_account_exists(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test duplicate detection finds existing account."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_account
        mock_session.execute.return_value = mock_result

        existing = await account_service._check_duplicate_account(
            platform=Platform.FACEBOOK,
            account_id="fb_account_123",
            user_id="user-123",
        )

        assert existing == sample_account

    @pytest.mark.asyncio
    async def test_check_duplicate_account_not_exists(
        self, account_service: AccountService, mock_session: AsyncMock
    ) -> None:
        """Test duplicate detection when no account exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        existing = await account_service._check_duplicate_account(
            platform=Platform.FACEBOOK,
            account_id="new_account",
            user_id="user123",
        )

        assert existing is None


class TestTokenExpiration:
    """Tests for token expiration checking."""

    @pytest.mark.asyncio
    async def test_get_expired_accounts(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test getting accounts with expired tokens."""
        sample_account.expires_at = datetime.utcnow() - timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_account]
        mock_session.execute.return_value = mock_result

        accounts = await account_service.get_expired_accounts()

        assert len(accounts) == 1
        assert accounts[0].is_token_expired is True

    @pytest.mark.asyncio
    async def test_get_expiring_soon_accounts(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
        sample_account: SocialAccount,
    ) -> None:
        """Test getting accounts with tokens expiring soon."""
        sample_account.expires_at = datetime.utcnow() + timedelta(minutes=30)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_account]
        mock_session.execute.return_value = mock_result

        accounts = await account_service.get_expiring_soon_accounts(
            threshold_minutes=60
        )

        assert len(accounts) == 1


class TestAccountStatistics:
    """Tests for account statistics."""

    @pytest.mark.asyncio
    async def test_get_user_account_count(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting count of user accounts."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        count = await account_service.get_user_account_count(user_id="user123")

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_verified_account_count(
        self,
        account_service: AccountService,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting count of verified accounts."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result

        count = await account_service.get_verified_account_count(user_id="user123")

        assert count == 2
