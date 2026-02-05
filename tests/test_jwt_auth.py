"""
Integration tests for JWT authentication flow.

Tests login endpoint, token validation, token refresh, logout,
token blacklisting, and session management functionality.
"""

import pytest
from httpx import AsyncClient

from src.api_gateway.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_success():
    """Test successful user login with JWT tokens."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567800",
                "username": "loginuser",
            },
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login_test@example.com",
                "password": "SecureP@ss123",
            },
        )

        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["email"] == "login_test@example.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_wrong_password():
    """Test login with correct email but wrong password."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong_pass@example.com",
                "password": "CorrectP@ss123",
                "phone_number": "+1234567801",
                "username": "wrongpassuser",
            },
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong_pass@example.com",
                "password": "WrongP@ss123",
            },
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_refresh_success():
    """Test successful token refresh."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567802",
                "username": "refreshuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        login_data = login_response.json()
        old_refresh_token = login_data["refresh_token"]

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"
        assert refresh_data["refresh_token"] != old_refresh_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_refresh_invalid_token():
    """Test token refresh with invalid refresh token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_success():
    """Test successful logout."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567803",
                "username": "logoutuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        logout_response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert "message" in logout_data
        assert "successfully" in logout_data["message"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_without_auth():
    """Test logout without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/logout",
            json={},
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_blacklisting():
    """Test that tokens are blacklisted after logout."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "blacklist_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567804",
                "username": "blacklistuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "blacklist_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        login_data = login_response.json()
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_sessions():
    """Test retrieving active user sessions."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessions_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567805",
                "username": "sessionsuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "sessions_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        sessions_response = await client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert sessions_response.status_code == 200
        data = sessions_response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_all_devices():
    """Test logging out from all devices."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout_all_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567806",
                "username": "logoutalluser",
            },
        )

        login_response1 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout_all_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token1 = login_response1.json()["access_token"]

        login_response2 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout_all_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        refresh_token2 = login_response2.json()["refresh_token"]

        logout_all_response = await client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token1}"},
        )

        assert logout_all_response.status_code == 200
        data = logout_all_response.json()
        assert "sessions_terminated" in data
        assert data["sessions_terminated"] >= 1

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token2},
        )

        assert refresh_response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test that multiple sessions can be created for same user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "multi_session_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567807",
                "username": "multisessionuser",
            },
        )

        login1 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "multi_session_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        assert login1.status_code == 200
        access_token1 = login1.json()["access_token"]

        login2 = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "multi_session_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        assert login2.status_code == 200

        sessions_response = await client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": f"Bearer {access_token1}"},
        )

        data = sessions_response.json()
        assert len(data["sessions"]) >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_rotation_on_refresh():
    """Test that refresh tokens are rotated (changed) on each refresh."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "rotation_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567808",
                "username": "rotationuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "rotation_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        tokens1 = login_response.json()

        refresh_response1 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens1["refresh_token"]},
        )
        tokens2 = refresh_response1.json()

        assert tokens2["refresh_token"] != tokens1["refresh_token"]
        assert tokens2["access_token"] != tokens1["access_token"]

        refresh_response2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens2["refresh_token"]},
        )
        tokens3 = refresh_response2.json()

        assert tokens3["refresh_token"] != tokens2["refresh_token"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_old_refresh_token_invalid_after_rotation():
    """Test that old refresh token becomes invalid after rotation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "old_token_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567809",
                "username": "oldtokenuser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "old_token_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        old_refresh_token = login_response.json()["refresh_token"]

        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

        old_token_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

        assert old_token_response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_info_includes_device_info():
    """Test that session info includes device fingerprint and IP."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "device_info_test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567810",
                "username": "deviceinfouser",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "device_info_test@example.com",
                "password": "SecureP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        sessions_response = await client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        data = sessions_response.json()
        assert len(data["sessions"]) >= 1
        session = data["sessions"][0]
        assert "device_fingerprint" in session
        assert "user_agent" in session
        assert "ip_address" in session
        assert "created_at" in session
        assert "last_activity_at" in session
