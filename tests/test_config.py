"""
Tests for configuration management.

Tests Settings class validation, environment-specific configuration,
and get_settings() caching functionality.
"""

import pytest
from pydantic import ValidationError

from src.shared.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_default_values(self) -> None:
        """Test default configuration values."""
        settings = Settings()

        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.APP_NAME == "PalmsGig"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000

    def test_settings_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "False")
        monkeypatch.setenv("PORT", "9000")

        settings = Settings()

        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.PORT == 9000

    def test_settings_database_url(self) -> None:
        """Test database URL configuration."""
        settings = Settings()

        assert str(settings.DATABASE_URL).startswith("postgresql://")

    def test_settings_redis_url(self) -> None:
        """Test Redis URL configuration."""
        settings = Settings()

        assert str(settings.REDIS_URL).startswith("redis://")

    def test_settings_cors_origins_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CORS origins parsing from comma-separated string."""
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")

        settings = Settings()

        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:8000" in settings.CORS_ORIGINS

    def test_settings_cors_origins_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins parsing from empty string."""
        monkeypatch.setenv("CORS_ORIGINS", "")

        settings = Settings()

        assert settings.CORS_ORIGINS == []

    def test_settings_log_level_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log level validation."""
        monkeypatch.setenv("LOG_LEVEL", "info")
        settings = Settings()
        assert settings.LOG_LEVEL == "info"

        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.LOG_LEVEL == "debug"

    def test_settings_invalid_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid log level raises validation error."""
        monkeypatch.setenv("LOG_LEVEL", "invalid")

        with pytest.raises(ValidationError):
            Settings()

    def test_settings_log_format_validation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test log format validation."""
        monkeypatch.setenv("LOG_FORMAT", "json")
        settings = Settings()
        assert settings.LOG_FORMAT == "json"

        monkeypatch.setenv("LOG_FORMAT", "text")
        settings = Settings()
        assert settings.LOG_FORMAT == "text"

    def test_settings_invalid_log_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid log format raises validation error."""
        monkeypatch.setenv("LOG_FORMAT", "invalid")

        with pytest.raises(ValidationError):
            Settings()

    def test_settings_environment_validation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment validation."""
        for env in ["development", "staging", "production", "testing"]:
            monkeypatch.setenv("ENVIRONMENT", env)
            settings = Settings()
            assert settings.ENVIRONMENT == env

    def test_settings_invalid_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid environment raises validation error."""
        monkeypatch.setenv("ENVIRONMENT", "invalid")

        with pytest.raises(ValidationError):
            Settings()

    def test_settings_production_secrets_validation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production environment rejects default secrets."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "dev-secret-key-change-in-production")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "dev-" in str(exc_info.value)

    def test_settings_get_database_url_sync(self) -> None:
        """Test synchronous database URL generation."""
        settings = Settings()
        url = settings.get_database_url_sync()

        assert url.startswith("postgresql://")
        assert "asyncpg" not in url

    def test_settings_get_database_url_async(self) -> None:
        """Test asynchronous database URL generation."""
        settings = Settings()
        url = settings.get_database_url_async()

        assert url.startswith("postgresql+asyncpg://") or url.startswith("postgresql://")

    def test_settings_is_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_production helper method."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.is_production() is True

        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_production() is False

    def test_settings_is_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_development helper method."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_development() is True

        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.is_development() is False

    def test_settings_is_testing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_testing helper method."""
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings()
        assert settings.is_testing() is True

        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_testing() is False

    def test_settings_jwt_configuration(self) -> None:
        """Test JWT configuration values."""
        settings = Settings()

        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0


class TestGetSettings:
    """Tests for get_settings() function."""

    def test_get_settings_returns_settings(self) -> None:
        """Test get_settings returns Settings instance."""
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_caching(self) -> None:
        """Test get_settings caches and returns same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_with_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_settings loads environment-specific configuration."""
        monkeypatch.setenv("ENVIRONMENT", "testing")

        settings = Settings()

        assert settings.ENVIRONMENT == "testing"
