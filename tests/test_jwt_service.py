"""
Unit tests for JWT service functionality.

Tests token generation, validation, expiry handling, blacklisting,
and refresh token rotation functionality.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt

from src.shared.config import Settings
from src.user_management.services.jwt import JWTService


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.JWT_SECRET = "test-secret-key-for-testing-only"
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    return settings


@pytest.fixture
def mock_redis():
    """Create mock Redis client for testing."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def jwt_service(mock_settings, mock_redis):
    """Create JWT service instance for testing."""
    return JWTService(settings=mock_settings, redis_client=mock_redis)


@pytest.mark.unit
def test_create_access_token(jwt_service, mock_settings):
    """Test creation of access token."""
    user_id = "test-user-123"

    token = jwt_service.create_access_token(user_id)

    assert token is not None
    assert isinstance(token, str)

    payload = jwt.decode(
        token, mock_settings.JWT_SECRET, algorithms=[mock_settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


@pytest.mark.unit
def test_create_access_token_with_claims(jwt_service, mock_settings):
    """Test creation of access token with additional claims."""
    user_id = "test-user-123"
    additional_claims = {"email": "test@example.com", "role": "admin"}

    token = jwt_service.create_access_token(user_id, additional_claims)

    payload = jwt.decode(
        token, mock_settings.JWT_SECRET, algorithms=[mock_settings.JWT_ALGORITHM]
    )
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "admin"


@pytest.mark.unit
def test_create_access_token_empty_user_id(jwt_service):
    """Test that creating token with empty user_id raises error."""
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        jwt_service.create_access_token("")


@pytest.mark.unit
def test_create_refresh_token(jwt_service, mock_settings):
    """Test creation of refresh token."""
    user_id = "test-user-123"

    token = jwt_service.create_refresh_token(user_id)

    assert token is not None
    assert isinstance(token, str)

    payload = jwt.decode(
        token, mock_settings.JWT_SECRET, algorithms=[mock_settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"
    assert "family" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


@pytest.mark.unit
def test_create_refresh_token_with_family(jwt_service, mock_settings):
    """Test creation of refresh token with specific family."""
    user_id = "test-user-123"
    token_family = "family-abc-123"

    token = jwt_service.create_refresh_token(user_id, token_family=token_family)

    payload = jwt.decode(
        token, mock_settings.JWT_SECRET, algorithms=[mock_settings.JWT_ALGORITHM]
    )
    assert payload["family"] == token_family


@pytest.mark.unit
def test_create_refresh_token_empty_user_id(jwt_service):
    """Test that creating refresh token with empty user_id raises error."""
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        jwt_service.create_refresh_token("")


@pytest.mark.unit
def test_decode_token(jwt_service, mock_settings):
    """Test decoding a valid token."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    payload = jwt_service.decode_token(token)

    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


@pytest.mark.unit
def test_decode_invalid_token(jwt_service):
    """Test decoding an invalid token."""
    with pytest.raises(Exception):
        jwt_service.decode_token("invalid.token.here")


@pytest.mark.unit
def test_decode_empty_token(jwt_service):
    """Test decoding empty token raises error."""
    with pytest.raises(ValueError, match="token cannot be empty"):
        jwt_service.decode_token("")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_access_token(jwt_service):
    """Test validation of access token."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    payload = await jwt_service.validate_access_token(token)

    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_access_token_wrong_type(jwt_service):
    """Test validation fails for refresh token when expecting access token."""
    user_id = "test-user-123"
    token = jwt_service.create_refresh_token(user_id)

    with pytest.raises(ValueError, match="not an access token"):
        await jwt_service.validate_access_token(token)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_refresh_token(jwt_service):
    """Test validation of refresh token."""
    user_id = "test-user-123"
    token = jwt_service.create_refresh_token(user_id)

    payload = await jwt_service.validate_refresh_token(token)

    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_refresh_token_wrong_type(jwt_service):
    """Test validation fails for access token when expecting refresh token."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    with pytest.raises(ValueError, match="not a refresh token"):
        await jwt_service.validate_refresh_token(token)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blacklist_token(jwt_service, mock_redis):
    """Test blacklisting a token."""
    jti = "test-jti-123"
    expires_in_seconds = 3600

    await jwt_service.blacklist_token(jti, expires_in_seconds)

    mock_redis.setex.assert_called_once_with(
        f"token:blacklist:{jti}", expires_in_seconds, "1"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blacklist_token_empty_jti(jwt_service):
    """Test that blacklisting with empty jti raises error."""
    with pytest.raises(ValueError, match="jti cannot be empty"):
        await jwt_service.blacklist_token("", 3600)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blacklist_token_negative_expiry(jwt_service):
    """Test that blacklisting with negative expiry is skipped."""
    await jwt_service.blacklist_token("test-jti", -100)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_blacklisted_true(jwt_service, mock_redis):
    """Test checking if token is blacklisted returns True."""
    mock_redis.exists.return_value = 1
    jti = "blacklisted-jti"

    is_blacklisted = await jwt_service.is_token_blacklisted(jti)

    assert is_blacklisted is True
    mock_redis.exists.assert_called_once_with(f"token:blacklist:{jti}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_blacklisted_false(jwt_service, mock_redis):
    """Test checking if token is blacklisted returns False."""
    mock_redis.exists.return_value = 0
    jti = "valid-jti"

    is_blacklisted = await jwt_service.is_token_blacklisted(jti)

    assert is_blacklisted is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_token_blacklisted_empty_jti(jwt_service):
    """Test checking blacklist with empty jti returns False."""
    is_blacklisted = await jwt_service.is_token_blacklisted("")

    assert is_blacklisted is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blacklist_family(jwt_service, mock_redis):
    """Test blacklisting a token family."""
    family = "family-abc-123"
    expires_in_seconds = 7 * 24 * 3600

    await jwt_service.blacklist_family(family, expires_in_seconds)

    mock_redis.setex.assert_called_once_with(
        f"token:family:blacklist:{family}", expires_in_seconds, "1"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blacklist_family_empty(jwt_service):
    """Test that blacklisting empty family raises error."""
    with pytest.raises(ValueError, match="family cannot be empty"):
        await jwt_service.blacklist_family("", 3600)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_family_blacklisted(jwt_service, mock_redis):
    """Test checking if family is blacklisted."""
    mock_redis.exists.return_value = 1
    family = "blacklisted-family"

    is_blacklisted = await jwt_service.is_family_blacklisted(family)

    assert is_blacklisted is True
    mock_redis.exists.assert_called_once_with(f"token:family:blacklist:{family}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_tokens(jwt_service):
    """Test refreshing tokens creates new token pair."""
    user_id = "test-user-123"
    old_refresh_token = jwt_service.create_refresh_token(user_id)

    new_access_token, new_refresh_token = await jwt_service.refresh_tokens(
        old_refresh_token
    )

    assert new_access_token is not None
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    new_access_payload = jwt_service.decode_token(new_access_token)
    assert new_access_payload["sub"] == user_id
    assert new_access_payload["type"] == "access"

    new_refresh_payload = jwt_service.decode_token(new_refresh_token)
    assert new_refresh_payload["sub"] == user_id
    assert new_refresh_payload["type"] == "refresh"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_tokens_preserves_family(jwt_service, mock_settings):
    """Test that token refresh preserves family."""
    user_id = "test-user-123"
    family = "family-xyz"
    old_refresh_token = jwt_service.create_refresh_token(user_id, token_family=family)

    _, new_refresh_token = await jwt_service.refresh_tokens(old_refresh_token)

    new_payload = jwt.decode(
        new_refresh_token,
        mock_settings.JWT_SECRET,
        algorithms=[mock_settings.JWT_ALGORITHM],
    )
    assert new_payload["family"] == family


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_tokens_blacklists_old_token(jwt_service, mock_redis):
    """Test that token refresh blacklists the old refresh token."""
    user_id = "test-user-123"
    old_refresh_token = jwt_service.create_refresh_token(user_id)

    await jwt_service.refresh_tokens(old_refresh_token)

    mock_redis.setex.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_token_rejects_blacklisted(jwt_service, mock_redis):
    """Test that validation rejects blacklisted token."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)
    payload = jwt_service.decode_token(token)
    jti = payload["jti"]

    mock_redis.exists.return_value = 1

    with pytest.raises(ValueError, match="revoked"):
        await jwt_service.validate_access_token(token)


@pytest.mark.unit
def test_get_token_expiry(jwt_service):
    """Test getting token expiration time."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    expiry = jwt_service.get_token_expiry(token)

    assert expiry is not None
    assert isinstance(expiry, datetime)
    assert expiry > datetime.utcnow()


@pytest.mark.unit
def test_get_token_expiry_invalid_token(jwt_service):
    """Test getting expiry of invalid token returns None."""
    expiry = jwt_service.get_token_expiry("invalid.token")

    assert expiry is None


@pytest.mark.unit
def test_get_token_remaining_seconds(jwt_service):
    """Test getting remaining seconds until token expires."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    remaining = jwt_service.get_token_remaining_seconds(token)

    assert remaining > 0
    assert remaining <= 30 * 60


@pytest.mark.unit
def test_get_token_remaining_seconds_invalid_token(jwt_service):
    """Test getting remaining seconds of invalid token returns 0."""
    remaining = jwt_service.get_token_remaining_seconds("invalid.token")

    assert remaining == 0


@pytest.mark.unit
def test_token_expiration(jwt_service, mock_settings):
    """Test that token expiration is set correctly."""
    user_id = "test-user-123"
    before_creation = datetime.utcnow()
    token = jwt_service.create_access_token(user_id)
    after_creation = datetime.utcnow()

    payload = jwt_service.decode_token(token)
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)

    expected_min = before_creation + timedelta(
        minutes=mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expected_max = after_creation + timedelta(
        minutes=mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    assert expected_min <= exp_datetime <= expected_max


@pytest.mark.unit
def test_refresh_token_expiration(jwt_service, mock_settings):
    """Test that refresh token expiration is set correctly."""
    user_id = "test-user-123"
    before_creation = datetime.utcnow()
    token = jwt_service.create_refresh_token(user_id)
    after_creation = datetime.utcnow()

    payload = jwt_service.decode_token(token)
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)

    expected_min = before_creation + timedelta(
        days=mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    expected_max = after_creation + timedelta(
        days=mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    assert expected_min <= exp_datetime <= expected_max


@pytest.mark.unit
def test_token_includes_jti(jwt_service):
    """Test that tokens include JTI (JWT ID)."""
    user_id = "test-user-123"
    token = jwt_service.create_access_token(user_id)

    payload = jwt_service.decode_token(token)

    assert "jti" in payload
    assert isinstance(payload["jti"], str)
    assert len(payload["jti"]) > 0


@pytest.mark.unit
def test_different_tokens_have_different_jtis(jwt_service):
    """Test that different tokens have different JTIs."""
    user_id = "test-user-123"
    token1 = jwt_service.create_access_token(user_id)
    token2 = jwt_service.create_access_token(user_id)

    payload1 = jwt_service.decode_token(token1)
    payload2 = jwt_service.decode_token(token2)

    assert payload1["jti"] != payload2["jti"]
