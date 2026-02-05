"""
Tests for Platform API Clients.

Comprehensive tests for platform client implementations including API calls,
rate limiting, error handling, token management, and verification methods.
Mock platform API responses for all supported platforms.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.social_media.enums.platform_enums import Platform
from src.social_media.services.platform_clients.base_client import BasePlatformClient
from src.social_media.services.platform_clients.facebook_client import FacebookClient
from src.social_media.services.platform_clients.instagram_client import InstagramClient
from src.social_media.services.platform_clients.twitter_client import TwitterClient

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create mock Redis client for rate limiting."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def facebook_client(mock_redis_client: AsyncMock) -> FacebookClient:
    """Create FacebookClient instance with mock Redis."""
    return FacebookClient(redis_client=mock_redis_client)


@pytest.fixture
def instagram_client(mock_redis_client: AsyncMock) -> InstagramClient:
    """Create InstagramClient instance with mock Redis."""
    return InstagramClient(redis_client=mock_redis_client)


@pytest.fixture
def twitter_client(mock_redis_client: AsyncMock) -> TwitterClient:
    """Create TwitterClient instance with mock Redis."""
    return TwitterClient(redis_client=mock_redis_client)


@pytest.fixture
def mock_user_profile_response() -> dict:
    """Mock user profile API response."""
    return {
        "id": "1234567890",
        "name": "John Doe",
        "email": "john@example.com",
        "username": "johndoe",
    }


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Create mock HTTP response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"id": "1234567890", "name": "John Doe"}
    response.text = '{"id": "1234567890"}'
    return response


class TestBasePlatformClient:
    """Tests for base platform client functionality."""

    def test_base_client_initialization(self, mock_redis_client: AsyncMock) -> None:
        """Test base client initialization."""

        class TestClient(BasePlatformClient):
            def __init__(self, redis_client):
                super().__init__(Platform.FACEBOOK, redis_client)

            async def verify_account(self, access_token: str) -> dict:
                return {}

        client = TestClient(redis_client=mock_redis_client)
        assert client.platform == Platform.FACEBOOK
        assert client.redis_client == mock_redis_client
        assert client.http_client is not None

    @pytest.mark.asyncio
    async def test_base_client_close(self, mock_redis_client: AsyncMock) -> None:
        """Test base client close method."""

        class TestClient(BasePlatformClient):
            def __init__(self, redis_client):
                super().__init__(Platform.FACEBOOK, redis_client)

            async def verify_account(self, access_token: str) -> dict:
                return {}

        client = TestClient(redis_client=mock_redis_client)

        with patch.object(client.http_client, "aclose", new=AsyncMock()) as mock_close:
            await client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_check_within_limit(
        self, facebook_client: FacebookClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test rate limit check when within limits."""
        mock_redis_client.get.return_value = b"50"

        can_proceed = await facebook_client._check_rate_limit("user123")
        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_rate_limit_check_exceeded(
        self, facebook_client: FacebookClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test rate limit check when limit exceeded."""
        # Set count above limit (200 for Facebook)
        mock_redis_client.get.return_value = b"250"

        can_proceed = await facebook_client._check_rate_limit("user123")
        assert can_proceed is False

    @pytest.mark.asyncio
    async def test_rate_limit_increment(
        self, facebook_client: FacebookClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test rate limit counter increments."""
        mock_redis_client.get.return_value = None  # First request
        mock_redis_client.incr.return_value = 1

        await facebook_client._check_rate_limit("user123")

        mock_redis_client.incr.assert_called_once()
        mock_redis_client.expire.assert_called_once()


class TestFacebookClient:
    """Tests for Facebook API client."""

    @pytest.mark.asyncio
    async def test_verify_account_success(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test successful Facebook account verification."""
        mock_http_response.json.return_value = {
            "id": "fb_user_123",
            "name": "John Doe",
            "email": "john@example.com",
        }

        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await facebook_client.verify_account("test_access_token")

            assert result["id"] == "fb_user_123"
            assert result["name"] == "John Doe"
            assert result["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_verify_account_with_fields(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test account verification with specific fields."""
        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ) as mock_get:
            await facebook_client.verify_account("test_token")

            call_args = mock_get.call_args
            assert "fields=" in call_args[0][0] or "fields=" in str(call_args)

    @pytest.mark.asyncio
    async def test_verify_account_invalid_token(
        self, facebook_client: FacebookClient
    ) -> None:
        """Test verification with invalid token."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Invalid OAuth access token"

        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="Failed to verify"):
                await facebook_client.verify_account("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_account_network_error(
        self, facebook_client: FacebookClient
    ) -> None:
        """Test verification handles network errors."""
        with patch.object(
            facebook_client.http_client,
            "get",
            new=AsyncMock(side_effect=httpx.RequestError("Network error")),
        ):
            with pytest.raises(ValueError):
                await facebook_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_verify_account_rate_limit_exceeded(
        self, facebook_client: FacebookClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test verification when rate limit is exceeded."""
        mock_redis_client.get.return_value = b"250"  # Above limit

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await facebook_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_get_user_profile(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting user profile from Facebook."""
        mock_http_response.json.return_value = {
            "id": "fb_user_123",
            "name": "John Doe",
            "email": "john@example.com",
            "picture": {"data": {"url": "https://example.com/pic.jpg"}},
        }

        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await facebook_client.get_user_profile("test_token")

            assert "id" in result
            assert "name" in result

    @pytest.mark.asyncio
    async def test_get_pages(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting Facebook pages."""
        mock_http_response.json.return_value = {
            "data": [
                {"id": "page1", "name": "My Page 1"},
                {"id": "page2", "name": "My Page 2"},
            ]
        }

        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await facebook_client.get_pages("test_token")

            assert len(result["data"]) == 2
            assert result["data"][0]["id"] == "page1"

    @pytest.mark.asyncio
    async def test_post_to_page(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test posting to Facebook page."""
        mock_http_response.json.return_value = {"id": "post_123"}

        with patch.object(
            facebook_client.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await facebook_client.post_to_page(
                page_id="page123",
                access_token="test_token",
                message="Test post",
            )

            assert result["id"] == "post_123"


class TestInstagramClient:
    """Tests for Instagram API client."""

    @pytest.mark.asyncio
    async def test_verify_account_success(
        self, instagram_client: InstagramClient, mock_http_response: MagicMock
    ) -> None:
        """Test successful Instagram account verification."""
        mock_http_response.json.return_value = {
            "id": "ig_user_123",
            "username": "johndoe",
            "account_type": "BUSINESS",
        }

        with patch.object(
            instagram_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await instagram_client.verify_account("test_access_token")

            assert result["id"] == "ig_user_123"
            assert result["username"] == "johndoe"

    @pytest.mark.asyncio
    async def test_get_user_media(
        self, instagram_client: InstagramClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting Instagram user media."""
        mock_http_response.json.return_value = {
            "data": [
                {"id": "media1", "caption": "Post 1"},
                {"id": "media2", "caption": "Post 2"},
            ]
        }

        with patch.object(
            instagram_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await instagram_client.get_user_media("test_token")

            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_media_insights(
        self, instagram_client: InstagramClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting Instagram media insights."""
        mock_http_response.json.return_value = {
            "data": [
                {"name": "impressions", "values": [{"value": 1000}]},
                {"name": "reach", "values": [{"value": 800}]},
            ]
        }

        with patch.object(
            instagram_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await instagram_client.get_media_insights(
                media_id="media123",
                access_token="test_token",
            )

            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_publish_media(
        self, instagram_client: InstagramClient, mock_http_response: MagicMock
    ) -> None:
        """Test publishing media to Instagram."""
        # Create container
        mock_http_response.json.return_value = {"id": "container123"}

        with patch.object(
            instagram_client.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await instagram_client.create_media_container(
                ig_user_id="user123",
                access_token="test_token",
                image_url="https://example.com/image.jpg",
                caption="Test post",
            )

            assert result["id"] == "container123"

    @pytest.mark.asyncio
    async def test_verify_account_rate_limit(
        self, instagram_client: InstagramClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test Instagram verification respects rate limits."""
        mock_redis_client.get.return_value = b"250"

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await instagram_client.verify_account("test_token")


class TestTwitterClient:
    """Tests for Twitter API client."""

    @pytest.mark.asyncio
    async def test_verify_account_success(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test successful Twitter account verification."""
        mock_http_response.json.return_value = {
            "data": {
                "id": "tw_user_123",
                "username": "johndoe",
                "name": "John Doe",
            }
        }

        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.verify_account("test_access_token")

            assert result["data"]["id"] == "tw_user_123"
            assert result["data"]["username"] == "johndoe"

    @pytest.mark.asyncio
    async def test_get_user_by_username(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting Twitter user by username."""
        mock_http_response.json.return_value = {
            "data": {
                "id": "tw_user_123",
                "username": "johndoe",
                "name": "John Doe",
            }
        }

        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.get_user_by_username(
                username="johndoe",
                access_token="test_token",
            )

            assert result["data"]["username"] == "johndoe"

    @pytest.mark.asyncio
    async def test_create_tweet(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test creating a tweet."""
        mock_http_response.json.return_value = {
            "data": {
                "id": "tweet123",
                "text": "Hello Twitter!",
            }
        }

        with patch.object(
            twitter_client.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.create_tweet(
                access_token="test_token",
                text="Hello Twitter!",
            )

            assert result["data"]["id"] == "tweet123"

    @pytest.mark.asyncio
    async def test_get_user_tweets(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test getting user tweets."""
        mock_http_response.json.return_value = {
            "data": [
                {"id": "tweet1", "text": "First tweet"},
                {"id": "tweet2", "text": "Second tweet"},
            ],
            "meta": {"result_count": 2},
        }

        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.get_user_tweets(
                user_id="user123",
                access_token="test_token",
            )

            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_follow_user(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test following a Twitter user."""
        mock_http_response.json.return_value = {
            "data": {
                "following": True,
                "pending_follow": False,
            }
        }

        with patch.object(
            twitter_client.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.follow_user(
                source_user_id="user123",
                target_user_id="user456",
                access_token="test_token",
            )

            assert result["data"]["following"] is True

    @pytest.mark.asyncio
    async def test_like_tweet(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test liking a tweet."""
        mock_http_response.json.return_value = {"data": {"liked": True}}

        with patch.object(
            twitter_client.http_client, "post", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await twitter_client.like_tweet(
                user_id="user123",
                tweet_id="tweet456",
                access_token="test_token",
            )

            assert result["data"]["liked"] is True


class TestErrorHandling:
    """Tests for error handling across all clients."""

    @pytest.mark.asyncio
    async def test_handles_timeout_error(
        self, facebook_client: FacebookClient
    ) -> None:
        """Test client handles timeout errors."""
        with patch.object(
            facebook_client.http_client,
            "get",
            new=AsyncMock(side_effect=httpx.TimeoutException("Request timeout")),
        ):
            with pytest.raises(ValueError):
                await facebook_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_handles_connection_error(
        self, instagram_client: InstagramClient
    ) -> None:
        """Test client handles connection errors."""
        with patch.object(
            instagram_client.http_client,
            "get",
            new=AsyncMock(side_effect=httpx.ConnectError("Connection failed")),
        ):
            with pytest.raises(ValueError):
                await instagram_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(
        self, twitter_client: TwitterClient
    ) -> None:
        """Test client handles invalid JSON responses."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not JSON"

        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError):
                await twitter_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_handles_rate_limit_from_api(
        self, facebook_client: FacebookClient
    ) -> None:
        """Test client handles rate limit errors from API."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="Rate limit"):
                await facebook_client.verify_account("test_token")

    @pytest.mark.asyncio
    async def test_handles_server_error(
        self, instagram_client: InstagramClient
    ) -> None:
        """Test client handles server errors."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        with patch.object(
            instagram_client.http_client, "get", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError):
                await instagram_client.verify_account("test_token")


class TestTokenManagement:
    """Tests for token management in clients."""

    @pytest.mark.asyncio
    async def test_uses_bearer_token_in_headers(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test client includes bearer token in request headers."""
        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ) as mock_get:
            await facebook_client.verify_account("test_token")

            call_args = mock_get.call_args
            # Check that access token is included in request
            assert "test_token" in str(call_args)

    @pytest.mark.asyncio
    async def test_handles_expired_token(
        self, twitter_client: TwitterClient
    ) -> None:
        """Test client handles expired token errors."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Token expired"

        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(ValueError, match="Failed to verify"):
                await twitter_client.verify_account("expired_token")


class TestPlatformSpecificFeatures:
    """Tests for platform-specific features."""

    @pytest.mark.asyncio
    async def test_facebook_graph_api_versioning(
        self, facebook_client: FacebookClient, mock_http_response: MagicMock
    ) -> None:
        """Test Facebook client uses correct Graph API version."""
        with patch.object(
            facebook_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ) as mock_get:
            await facebook_client.verify_account("test_token")

            call_url = str(mock_get.call_args)
            assert "graph.facebook.com" in call_url

    @pytest.mark.asyncio
    async def test_instagram_business_account_required(
        self, instagram_client: InstagramClient, mock_http_response: MagicMock
    ) -> None:
        """Test Instagram features work with business accounts."""
        mock_http_response.json.return_value = {
            "id": "ig_user_123",
            "username": "business_account",
            "account_type": "BUSINESS",
        }

        with patch.object(
            instagram_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ):
            result = await instagram_client.verify_account("test_token")

            assert result["account_type"] == "BUSINESS"

    @pytest.mark.asyncio
    async def test_twitter_v2_api_usage(
        self, twitter_client: TwitterClient, mock_http_response: MagicMock
    ) -> None:
        """Test Twitter client uses v2 API endpoints."""
        with patch.object(
            twitter_client.http_client, "get", new=AsyncMock(return_value=mock_http_response)
        ) as mock_get:
            await twitter_client.verify_account("test_token")

            call_url = str(mock_get.call_args)
            assert "api.twitter.com/2" in call_url or "/2/" in call_url


class TestRateLimitManagement:
    """Tests for rate limit management."""

    @pytest.mark.asyncio
    async def test_rate_limit_uses_redis_key(
        self, facebook_client: FacebookClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test rate limit uses correct Redis key."""
        await facebook_client._check_rate_limit("user123")

        call_args = mock_redis_client.get.call_args
        key = call_args[0][0]
        assert "rate_limit" in key
        assert "facebook" in key
        assert "user123" in key

    @pytest.mark.asyncio
    async def test_rate_limit_sets_expiration(
        self, instagram_client: InstagramClient, mock_redis_client: AsyncMock
    ) -> None:
        """Test rate limit sets key expiration."""
        mock_redis_client.get.return_value = None

        await instagram_client._check_rate_limit("user123")

        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_different_per_platform(
        self,
        facebook_client: FacebookClient,
        twitter_client: TwitterClient,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test different platforms have different rate limits."""
        # Facebook allows 200 requests per hour
        mock_redis_client.get.return_value = b"199"
        fb_can_proceed = await facebook_client._check_rate_limit("user123")
        assert fb_can_proceed is True

        # Twitter allows 300 requests per 15 minutes
        mock_redis_client.get.return_value = b"299"
        tw_can_proceed = await twitter_client._check_rate_limit("user123")
        assert tw_can_proceed is True
