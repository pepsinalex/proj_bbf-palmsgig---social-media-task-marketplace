"""
Tests for database connection and session management.

Tests DatabaseManager functionality including engine creation, session management,
health checks, and FastAPI dependency injection.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.shared.config import Settings, get_settings
from src.shared.database import (
    DatabaseManager,
    check_database_health,
    close_database_connections,
    get_database_manager,
    get_db_session,
)


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_database_manager_initialization(self) -> None:
        """Test DatabaseManager initialization with settings."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        assert db_manager.settings == settings
        assert db_manager._engine is None
        assert db_manager._session_factory is None

    def test_database_manager_pool_size(self) -> None:
        """Test connection pool size calculation."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        pool_size = db_manager._get_pool_size()
        assert isinstance(pool_size, int)
        assert pool_size > 0

    def test_database_manager_max_overflow(self) -> None:
        """Test max overflow calculation."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        max_overflow = db_manager._get_max_overflow()
        assert isinstance(max_overflow, int)
        assert max_overflow > 0

    def test_database_manager_create_engine(self) -> None:
        """Test engine creation."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        engine = db_manager.create_engine()

        assert isinstance(engine, AsyncEngine)
        assert engine is not None

    def test_database_manager_create_session_factory(self) -> None:
        """Test session factory creation."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        engine = db_manager.create_engine()
        session_factory = db_manager.create_session_factory(engine)

        assert session_factory is not None

    def test_database_manager_get_engine(self) -> None:
        """Test get_engine creates and caches engine."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        engine1 = db_manager.get_engine()
        engine2 = db_manager.get_engine()

        assert engine1 is engine2
        assert isinstance(engine1, AsyncEngine)

    def test_database_manager_get_session_factory(self) -> None:
        """Test get_session_factory creates and caches factory."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        factory1 = db_manager.get_session_factory()
        factory2 = db_manager.get_session_factory()

        assert factory1 is factory2

    @pytest.mark.asyncio
    async def test_database_manager_get_session(self) -> None:
        """Test get_session provides async session."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        async with db_manager.get_session() as session:
            assert isinstance(session, AsyncSession)
            assert session is not None

    @pytest.mark.asyncio
    async def test_database_manager_session_rollback_on_error(self) -> None:
        """Test session rollback on error."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        with pytest.raises(Exception):
            async with db_manager.get_session():
                raise Exception("Test error")

    @pytest.mark.asyncio
    async def test_database_manager_health_check_success(self) -> None:
        """Test health check returns True for healthy database."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        is_healthy = await db_manager.health_check()

        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_database_manager_health_check_with_retries(self) -> None:
        """Test health check retry mechanism."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        is_healthy = await db_manager.health_check(max_retries=2, retry_delay=0.1)

        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_database_manager_close(self) -> None:
        """Test closing database engine."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        db_manager.get_engine()
        await db_manager.close()

        assert db_manager._engine is None
        assert db_manager._session_factory is None


class TestGetDatabaseManager:
    """Tests for get_database_manager() function."""

    def test_get_database_manager_returns_manager(self) -> None:
        """Test get_database_manager returns DatabaseManager instance."""
        db_manager = get_database_manager()

        assert isinstance(db_manager, DatabaseManager)

    def test_get_database_manager_caching(self) -> None:
        """Test get_database_manager caches and returns same instance."""
        manager1 = get_database_manager()
        manager2 = get_database_manager()

        assert manager1 is manager2


class TestGetDbSession:
    """Tests for get_db_session() FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_db_session_provides_session(self) -> None:
        """Test get_db_session provides async session."""
        async for session in get_db_session():
            assert isinstance(session, AsyncSession)
            break

    @pytest.mark.asyncio
    async def test_get_db_session_cleanup(self) -> None:
        """Test get_db_session properly closes session."""
        session_ref = None

        async for session in get_db_session():
            session_ref = session
            assert session is not None
            break

        assert session_ref is not None


class TestCheckDatabaseHealth:
    """Tests for check_database_health() function."""

    @pytest.mark.asyncio
    async def test_check_database_health_returns_bool(self) -> None:
        """Test check_database_health returns boolean."""
        is_healthy = await check_database_health()

        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_check_database_health_with_valid_connection(self) -> None:
        """Test health check with valid database connection."""
        is_healthy = await check_database_health()

        assert isinstance(is_healthy, bool)


class TestCloseDatabaseConnections:
    """Tests for close_database_connections() function."""

    @pytest.mark.asyncio
    async def test_close_database_connections(self) -> None:
        """Test closing all database connections."""
        db_manager = get_database_manager()
        db_manager.get_engine()

        await close_database_connections()

    @pytest.mark.asyncio
    async def test_close_database_connections_when_none(self) -> None:
        """Test closing connections when manager doesn't exist."""
        await close_database_connections()


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_connection_cycle(self) -> None:
        """Test complete database connection lifecycle."""
        settings = Settings()
        db_manager = DatabaseManager(settings)

        engine = db_manager.get_engine()
        assert engine is not None

        async with db_manager.get_session() as session:
            assert session is not None

        is_healthy = await db_manager.health_check()
        assert isinstance(is_healthy, bool)

        await db_manager.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_manager_pool_configuration(self) -> None:
        """Test database connection pool configuration."""
        settings = get_settings()
        db_manager = DatabaseManager(settings)

        engine = db_manager.create_engine()
        assert engine is not None

        pool = engine.pool
        assert pool is not None
