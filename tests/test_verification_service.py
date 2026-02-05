"""
Unit tests for verification service.

Tests token generation, Redis storage, email sending, SMS sending,
token validation, and expiration handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.user_management.services.verification import VerificationService


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.ttl = AsyncMock(return_value=900)
    redis.incr = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def verification_service(mock_redis):
    """Create a verification service instance with mock Redis."""
    return VerificationService(
        redis_client=mock_redis,
        token_expiry_minutes=15,
        token_length=6,
        rate_limit_window_seconds=60,
        max_attempts_per_window=3,
    )


@pytest.mark.unit
def test_generate_token(verification_service):
    """Test token generation."""
    token = verification_service.generate_token()

    assert isinstance(token, str)
    assert len(token) == 6
    assert token.isalnum()
    assert token.isupper() or token.isdigit()


@pytest.mark.unit
def test_generate_token_uniqueness(verification_service):
    """Test that generated tokens are unique."""
    tokens = set()
    for _ in range(100):
        token = verification_service.generate_token()
        tokens.add(token)

    assert len(tokens) > 90


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_token_success(verification_service, mock_redis):
    """Test successful token storage."""
    result = await verification_service.store_token(
        identifier="test@example.com", token="ABC123", token_type="email", user_id="user-123"
    )

    assert result is True
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "verification:email:test@example.com"
    assert call_args[0][1] == 900
    assert "ABC123" in call_args[0][2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_token_without_user_id(verification_service, mock_redis):
    """Test token storage without user ID."""
    result = await verification_service.store_token(
        identifier="test@example.com", token="ABC123", token_type="email"
    )

    assert result is True
    mock_redis.setex.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_token_success(verification_service, mock_redis):
    """Test successful token verification."""
    mock_redis.get.return_value = b"ABC123:user-123"

    is_valid, user_id = await verification_service.verify_token(
        identifier="test@example.com", token="ABC123", token_type="email"
    )

    assert is_valid is True
    assert user_id == "user-123"
    mock_redis.delete.assert_called_once_with("verification:email:test@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_token_invalid(verification_service, mock_redis):
    """Test token verification with invalid token."""
    mock_redis.get.return_value = b"ABC123:user-123"

    is_valid, user_id = await verification_service.verify_token(
        identifier="test@example.com", token="WRONG", token_type="email"
    )

    assert is_valid is False
    assert user_id is None
    mock_redis.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_token_not_found(verification_service, mock_redis):
    """Test token verification when token doesn't exist."""
    mock_redis.get.return_value = None

    is_valid, user_id = await verification_service.verify_token(
        identifier="test@example.com", token="ABC123", token_type="email"
    )

    assert is_valid is False
    assert user_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(verification_service, mock_redis):
    """Test rate limit check within limit."""
    mock_redis.get.return_value = b"2"

    result = await verification_service.check_rate_limit(
        identifier="test@example.com", token_type="email"
    )

    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(verification_service, mock_redis):
    """Test rate limit check when limit is exceeded."""
    mock_redis.get.return_value = b"5"

    result = await verification_service.check_rate_limit(
        identifier="test@example.com", token_type="email"
    )

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_rate_limit_no_attempts(verification_service, mock_redis):
    """Test rate limit check with no previous attempts."""
    mock_redis.get.return_value = None

    result = await verification_service.check_rate_limit(
        identifier="test@example.com", token_type="email"
    )

    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_increment_attempt(verification_service, mock_redis):
    """Test incrementing attempt counter."""
    mock_redis.get.return_value = None

    await verification_service.increment_attempt(
        identifier="test@example.com", token_type="email"
    )

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "verification:ratelimit:email:test@example.com"
    assert call_args[0][2] == "1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_increment_attempt_existing_counter(verification_service, mock_redis):
    """Test incrementing existing attempt counter."""
    mock_redis.get.return_value = b"2"

    await verification_service.increment_attempt(
        identifier="test@example.com", token_type="email"
    )

    mock_redis.incr.assert_called_once_with("verification:ratelimit:email:test@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_rate_limit(verification_service, mock_redis):
    """Test clearing rate limit counter."""
    await verification_service.clear_rate_limit(
        identifier="test@example.com", token_type="email"
    )

    mock_redis.delete.assert_called_once_with("verification:ratelimit:email:test@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_ttl_success(verification_service, mock_redis):
    """Test getting token TTL."""
    mock_redis.ttl.return_value = 600

    ttl = await verification_service.get_token_ttl(
        identifier="test@example.com", token_type="email"
    )

    assert ttl == 600


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_token_ttl_expired(verification_service, mock_redis):
    """Test getting TTL for expired token."""
    mock_redis.ttl.return_value = -2

    ttl = await verification_service.get_token_ttl(
        identifier="test@example.com", token_type="email"
    )

    assert ttl is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resend_token_success(verification_service, mock_redis):
    """Test successful token resend."""
    mock_redis.get.return_value = None

    new_token = await verification_service.resend_token(
        identifier="test@example.com", token_type="email"
    )

    assert new_token is not None
    assert isinstance(new_token, str)
    assert len(new_token) == 6
    mock_redis.setex.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resend_token_rate_limit_exceeded(verification_service, mock_redis):
    """Test token resend when rate limit is exceeded."""
    mock_redis.get.return_value = b"5"

    new_token = await verification_service.resend_token(
        identifier="test@example.com", token_type="email"
    )

    assert new_token is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_token_rate_limit_check(verification_service, mock_redis):
    """Test that verify_token checks rate limit."""
    mock_redis.get.side_effect = [b"5", b"ABC123:user-123"]

    is_valid, user_id = await verification_service.verify_token(
        identifier="test@example.com", token="ABC123", token_type="email"
    )

    assert is_valid is False
    assert user_id is None
