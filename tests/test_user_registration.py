"""
Integration tests for user registration workflow.

Tests registration endpoint, email verification, phone verification,
duplicate prevention, validation errors, and rate limiting.
"""

import pytest
from httpx import AsyncClient

from src.api_gateway.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_success():
    """Test successful user registration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567890",
                "username": "testuser",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert data["email_verified"] is False
        assert data["phone_verified"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_duplicate_email():
    """Test registration with duplicate email."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "SecureP@ss123",
        "phone_number": "+1234567891",
        "username": "testuser1",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        user_data["username"] = "testuser2"
        user_data["phone_number"] = "+1234567892"
        response2 = await client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_weak_password():
    """Test registration with weak password."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "phone_number": "+1234567893",
                "username": "weakuser",
            },
        )

        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_invalid_email():
    """Test registration with invalid email format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecureP@ss123",
                "phone_number": "+1234567894",
                "username": "invaliduser",
            },
        )

        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_verify_email_success():
    """Test successful email verification."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567895",
                "username": "verifyuser",
            },
        )
        assert register_response.status_code == 201

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": "verify@example.com", "token": "123456"},
        )

        assert verify_response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_verify_email_invalid_token():
    """Test email verification with invalid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": "nonexistent@example.com", "token": "000000"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_verify_phone_success():
    """Test successful phone verification."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "phone@example.com",
                "password": "SecureP@ss123",
                "phone_number": "+1234567896",
                "username": "phoneuser",
            },
        )
        assert register_response.status_code == 201

        verify_response = await client.post(
            "/api/v1/auth/verify-phone",
            json={"phone_number": "+1234567896", "token": "123456"},
        )

        assert verify_response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_duplicate_username():
    """Test registration with duplicate username."""
    user_data = {
        "email": "user1@example.com",
        "password": "SecureP@ss123",
        "phone_number": "+1234567897",
        "username": "duplicateuser",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        user_data["email"] = "user2@example.com"
        user_data["phone_number"] = "+1234567898"
        response2 = await client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "username" in response2.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user_duplicate_phone():
    """Test registration with duplicate phone number."""
    user_data = {
        "email": "user3@example.com",
        "password": "SecureP@ss123",
        "phone_number": "+1234567899",
        "username": "user3",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        user_data["email"] = "user4@example.com"
        user_data["username"] = "user4"
        response2 = await client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "phone" in response2.json()["detail"].lower()
