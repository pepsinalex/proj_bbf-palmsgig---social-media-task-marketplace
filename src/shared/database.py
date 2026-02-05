"""
Database connection and session management with SQLAlchemy async.

This module provides async database connectivity, connection pooling, session management,
and health check functionality for the PalmsGig platform.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.shared.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager for SQLAlchemy async engine and session factory.

    Handles engine creation, connection pooling, and session lifecycle management.
    Provides retry logic for transient connection failures.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize database manager with settings.

        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _get_pool_class(self) -> type[QueuePool] | type[NullPool]:
        """
        Get appropriate connection pool class based on environment.

        Returns:
            Pool class (QueuePool for production, NullPool for testing)
        """
        if self.settings.is_testing():
            return NullPool
        return QueuePool

    def _get_pool_size(self) -> int:
        """
        Get connection pool size based on environment.

        Returns:
            Pool size (workers * 2 for production, 5 for other environments)
        """
        if self.settings.is_production():
            return self.settings.WORKERS * 2
        return 5

    def _get_max_overflow(self) -> int:
        """
        Get maximum overflow connections based on environment.

        Returns:
            Max overflow (workers for production, 10 for other environments)
        """
        if self.settings.is_production():
            return self.settings.WORKERS
        return 10

    def create_engine(self) -> AsyncEngine:
        """
        Create async SQLAlchemy engine with connection pooling.

        Configures engine with appropriate pool settings, timeouts, and logging.

        Returns:
            Configured async engine instance

        Raises:
            Exception: If engine creation fails
        """
        try:
            database_url = self.settings.get_database_url_async()

            pool_class = self._get_pool_class()
            pool_size = self._get_pool_size()
            max_overflow = self._get_max_overflow()

            engine_kwargs: dict[str, Any] = {
                "url": database_url,
                "echo": self.settings.DEBUG,
                "future": True,
                "pool_pre_ping": True,
            }

            if pool_class == QueuePool:
                engine_kwargs.update(
                    {
                        "poolclass": QueuePool,
                        "pool_size": pool_size,
                        "max_overflow": max_overflow,
                        "pool_timeout": 30,
                        "pool_recycle": 3600,
                    }
                )
            else:
                engine_kwargs["poolclass"] = NullPool

            engine = create_async_engine(**engine_kwargs)

            logger.info(
                "Database engine created",
                extra={
                    "pool_class": pool_class.__name__,
                    "pool_size": pool_size if pool_class == QueuePool else "N/A",
                    "max_overflow": max_overflow if pool_class == QueuePool else "N/A",
                    "environment": self.settings.ENVIRONMENT,
                },
            )

            return engine

        except Exception as e:
            logger.error(
                "Failed to create database engine",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def create_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        """
        Create async session factory from engine.

        Args:
            engine: Async engine instance

        Returns:
            Configured session factory
        """
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Session factory created")

        return session_factory

    def get_engine(self) -> AsyncEngine:
        """
        Get or create async engine instance.

        Returns:
            Async engine instance

        Raises:
            Exception: If engine cannot be created
        """
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get or create session factory.

        Returns:
            Session factory instance

        Raises:
            Exception: If session factory cannot be created
        """
        if self._session_factory is None:
            engine = self.get_engine()
            self._session_factory = self.create_session_factory(engine)
        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup.

        Provides context manager for session lifecycle management with
        automatic rollback on errors.

        Yields:
            Async session instance

        Raises:
            SQLAlchemyError: If session operations fail

        Example:
            >>> async with db_manager.get_session() as session:
            ...     result = await session.execute(select(User))
        """
        session_factory = self.get_session_factory()
        session = session_factory()

        try:
            logger.debug("Database session created")
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(
                "Database session rolled back",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        except Exception as e:
            await session.rollback()
            logger.error(
                "Database session rolled back due to unexpected error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")

    async def health_check(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Check database connectivity with retry logic.

        Attempts to execute a simple query to verify database connectivity.
        Retries on transient failures with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds

        Returns:
            True if database is healthy, False otherwise

        Example:
            >>> is_healthy = await db_manager.health_check()
            >>> if not is_healthy:
            ...     logger.error("Database is not healthy")
        """
        import asyncio

        from sqlalchemy import text

        for attempt in range(1, max_retries + 1):
            try:
                async with self.get_session() as session:
                    await session.execute(text("SELECT 1"))
                    logger.info(
                        "Database health check passed",
                        extra={
                            "attempt": attempt,
                            "max_retries": max_retries,
                        },
                    )
                    return True
            except (OperationalError, DBAPIError) as e:
                logger.warning(
                    "Database health check failed",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if attempt < max_retries:
                    delay = retry_delay * (2 ** (attempt - 1))
                    logger.info(
                        f"Retrying database health check in {delay}s",
                        extra={
                            "delay": delay,
                            "next_attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Database health check failed after all retries",
                        extra={
                            "max_retries": max_retries,
                            "error": str(e),
                        },
                    )
                    return False
            except Exception as e:
                logger.error(
                    "Database health check failed with unexpected error",
                    extra={
                        "attempt": attempt,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                return False

        return False

    async def close(self) -> None:
        """
        Close database engine and cleanup resources.

        Should be called on application shutdown to properly close
        all database connections.
        """
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine disposed")
            self._engine = None
            self._session_factory = None


_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Creates and caches the database manager singleton.

    Returns:
        Database manager instance
    """
    global _db_manager

    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(settings)
        logger.info("Database manager initialized")

    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session injection.

    Provides async database session for FastAPI route handlers with
    automatic cleanup and error handling.

    Yields:
        Async session instance

    Raises:
        SQLAlchemyError: If session operations fail

    Example:
        >>> @app.get("/users")
        >>> async def get_users(session: AsyncSession = Depends(get_db_session)):
        ...     result = await session.execute(select(User))
        ...     return result.scalars().all()
    """
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(
                "Database session error in dependency",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in database session dependency",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise


async def check_database_health() -> bool:
    """
    Check database health for monitoring and health check endpoints.

    Returns:
        True if database is healthy, False otherwise

    Example:
        >>> @app.get("/health/database")
        >>> async def database_health():
        ...     is_healthy = await check_database_health()
        ...     if is_healthy:
        ...         return {"status": "healthy"}
        ...     raise HTTPException(status_code=503, detail="Database unhealthy")
    """
    db_manager = get_database_manager()
    return await db_manager.health_check()


async def close_database_connections() -> None:
    """
    Close all database connections on application shutdown.

    Should be called in FastAPI lifespan or shutdown event.

    Example:
        >>> @app.on_event("shutdown")
        >>> async def shutdown():
        ...     await close_database_connections()
    """
    global _db_manager

    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
        logger.info("Database connections closed")
