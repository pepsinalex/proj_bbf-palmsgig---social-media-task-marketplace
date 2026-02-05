"""
Application configuration management using Pydantic Settings.

This module provides centralized configuration management for the PalmsGig platform,
handling environment variables, validation, and environment-specific overrides.
"""

import logging
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Provides configuration for database, Redis, security, CORS, and general app settings.
    Implements validation and default values for all configuration parameters.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://palmsgig:palmsgig@localhost:5432/palmsgig",
        description="PostgreSQL database connection URL",
    )

    # Redis Configuration
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and sessions",
    )

    # Security Configuration
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-use-random-secure-key",
        min_length=32,
        description="Secret key for cryptographic operations",
    )

    JWT_SECRET: str = Field(
        default="dev-jwt-secret-change-in-production-use-random-secure-key",
        min_length=32,
        description="Secret key for JWT token signing",
    )

    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing",
    )

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        gt=0,
        description="Access token expiration time in minutes",
    )

    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        gt=0,
        description="Refresh token expiration time in days",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Application Configuration
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag",
    )

    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )

    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="API version 1 prefix",
    )

    APP_NAME: str = Field(
        default="PalmsGig",
        description="Application name",
    )

    APP_VERSION: str = Field(
        default="0.1.0",
        description="Application version",
    )

    # Server Configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host",
    )

    PORT: int = Field(
        default=8000,
        gt=0,
        lt=65536,
        description="Server port",
    )

    WORKERS: int = Field(
        default=4,
        gt=0,
        description="Number of worker processes",
    )

    RELOAD: bool = Field(
        default=False,
        description="Auto-reload on code changes",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="info",
        description="Logging level",
    )

    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json, text)",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """
        Parse CORS origins from string or list.

        Handles comma-separated string input and converts to list of strings.

        Args:
            v: Input value (string or list)

        Returns:
            List of CORS origin strings

        Raises:
            ValueError: If value cannot be parsed
        """
        if isinstance(v, str):
            if not v.strip():
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        else:
            raise ValueError(f"Invalid CORS_ORIGINS format: {type(v)}")

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate and normalize log level.

        Args:
            v: Log level string

        Returns:
            Normalized log level string in lowercase

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        normalized = v.lower()
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: {v}. Must be one of {', '.join(valid_levels)}"
            )
        return normalized

    @field_validator("LOG_FORMAT", mode="after")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """
        Validate log format.

        Args:
            v: Log format string

        Returns:
            Validated log format string in lowercase

        Raises:
            ValueError: If log format is invalid
        """
        valid_formats = {"json", "text"}
        normalized = v.lower()
        if normalized not in valid_formats:
            raise ValueError(
                f"Invalid LOG_FORMAT: {v}. Must be one of {', '.join(valid_formats)}"
            )
        return normalized

    @field_validator("ENVIRONMENT", mode="after")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        Validate environment setting.

        Args:
            v: Environment string

        Returns:
            Validated environment string in lowercase

        Raises:
            ValueError: If environment is invalid
        """
        valid_environments = {"development", "staging", "production", "testing"}
        normalized = v.lower()
        if normalized not in valid_environments:
            raise ValueError(
                f"Invalid ENVIRONMENT: {v}. Must be one of {', '.join(valid_environments)}"
            )
        return normalized

    @field_validator("SECRET_KEY", "JWT_SECRET", mode="after")
    @classmethod
    def validate_production_secrets(cls, v: str, info) -> str:
        """
        Validate that production secrets are not using default values.

        Args:
            v: Secret key value
            info: Validation info

        Returns:
            Validated secret key

        Raises:
            ValueError: If using default secrets in production
        """
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and "dev-" in v:
            field_name = info.field_name
            raise ValueError(
                f"{field_name} must not use default development value in production. "
                f"Generate a secure random key using: "
                f"python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v

    def get_database_url_sync(self) -> str:
        """
        Get synchronous database URL.

        Returns:
            Database URL string for synchronous connections
        """
        url = str(self.DATABASE_URL)
        return url.replace("postgresql+asyncpg://", "postgresql://")

    def get_database_url_async(self) -> str:
        """
        Get asynchronous database URL.

        Returns:
            Database URL string for async connections
        """
        url = str(self.DATABASE_URL)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    def is_production(self) -> bool:
        """
        Check if running in production environment.

        Returns:
            True if environment is production, False otherwise
        """
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """
        Check if running in development environment.

        Returns:
            True if environment is development, False otherwise
        """
        return self.ENVIRONMENT == "development"

    def is_testing(self) -> bool:
        """
        Check if running in testing environment.

        Returns:
            True if environment is testing, False otherwise
        """
        return self.ENVIRONMENT == "testing"

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialization hook for additional setup.

        Logs configuration summary after initialization.

        Args:
            __context: Pydantic context (unused)
        """
        logger.info(
            "Configuration loaded",
            extra={
                "environment": self.ENVIRONMENT,
                "debug": self.DEBUG,
                "app_name": self.APP_NAME,
                "app_version": self.APP_VERSION,
                "log_level": self.LOG_LEVEL,
            },
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    Uses LRU cache to ensure settings are loaded only once and reused across
    the application lifecycle. This prevents repeated file I/O and validation.

    Returns:
        Settings instance with loaded configuration

    Raises:
        ValidationError: If configuration validation fails
        Exception: If settings cannot be loaded

    Example:
        >>> settings = get_settings()
        >>> print(settings.DATABASE_URL)
        postgresql://palmsgig:palmsgig@localhost:5432/palmsgig
    """
    try:
        settings = Settings()
        logger.info(
            "Settings initialized successfully",
            extra={
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
            },
        )
        return settings
    except ValidationError as e:
        logger.error(
            "Configuration validation failed",
            extra={
                "errors": e.errors(),
                "error_count": e.error_count(),
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to load settings",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise
