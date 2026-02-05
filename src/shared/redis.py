"""
Redis connection and client management with async support.

This module provides async Redis connectivity, connection pooling, retry logic,
health checks, and utility functions for caching operations.
"""

import json
import logging
from typing import Any

from redis import asyncio as aioredis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from src.shared.config import Settings, get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis manager for async client and connection pool management.

    Handles client creation, connection pooling, retry logic, and caching utilities.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Redis manager with settings.

        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self._client: Redis | None = None
        self._pool: ConnectionPool | None = None

    def _get_pool_max_connections(self) -> int:
        """
        Get maximum connections for pool based on environment.

        Returns:
            Max connections (workers * 4 for production, 10 for other environments)
        """
        if self.settings.is_production():
            return self.settings.WORKERS * 4
        return 10

    def _get_socket_timeout(self) -> float:
        """
        Get socket timeout based on environment.

        Returns:
            Timeout in seconds (5.0 for production, 10.0 for other environments)
        """
        if self.settings.is_production():
            return 5.0
        return 10.0

    def create_pool(self) -> ConnectionPool:
        """
        Create Redis connection pool with appropriate settings.

        Returns:
            Configured connection pool instance

        Raises:
            Exception: If pool creation fails
        """
        try:
            redis_url = str(self.settings.REDIS_URL)
            max_connections = self._get_pool_max_connections()
            socket_timeout = self._get_socket_timeout()

            pool = ConnectionPool.from_url(
                redis_url,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_timeout,
                socket_keepalive=True,
                health_check_interval=30,
                decode_responses=True,
                encoding="utf-8",
            )

            logger.info(
                "Redis connection pool created",
                extra={
                    "max_connections": max_connections,
                    "socket_timeout": socket_timeout,
                    "environment": self.settings.ENVIRONMENT,
                },
            )

            return pool

        except Exception as e:
            logger.error(
                "Failed to create Redis connection pool",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def create_client(self, pool: ConnectionPool) -> Redis:
        """
        Create Redis client from connection pool.

        Args:
            pool: Connection pool instance

        Returns:
            Configured Redis client
        """
        client = Redis(connection_pool=pool)

        logger.info("Redis client created")

        return client

    def get_client(self) -> Redis:
        """
        Get or create Redis client instance.

        Returns:
            Redis client instance

        Raises:
            Exception: If client cannot be created
        """
        if self._client is None:
            if self._pool is None:
                self._pool = self.create_pool()
            self._client = self.create_client(self._pool)

        return self._client

    async def health_check(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Check Redis connectivity with retry logic.

        Attempts to ping Redis server to verify connectivity.
        Retries on transient failures with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds

        Returns:
            True if Redis is healthy, False otherwise

        Example:
            >>> is_healthy = await redis_manager.health_check()
            >>> if not is_healthy:
            ...     logger.error("Redis is not healthy")
        """
        import asyncio

        client = self.get_client()

        for attempt in range(1, max_retries + 1):
            try:
                await client.ping()
                logger.info(
                    "Redis health check passed",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                    },
                )
                return True
            except (ConnectionError, TimeoutError) as e:
                logger.warning(
                    "Redis health check failed",
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
                        f"Retrying Redis health check in {delay}s",
                        extra={
                            "delay": delay,
                            "next_attempt": attempt + 1,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Redis health check failed after all retries",
                        extra={
                            "max_retries": max_retries,
                            "error": str(e),
                        },
                    )
                    return False
            except Exception as e:
                logger.error(
                    "Redis health check failed with unexpected error",
                    extra={
                        "attempt": attempt,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                return False

        return False

    async def set_cache(
        self, key: str, value: Any, ttl: int | None = None, serializer: str = "json"
    ) -> bool:
        """
        Set cache value with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
            serializer: Serialization format ("json" or "str")

        Returns:
            True if successful, False otherwise

        Example:
            >>> await redis_manager.set_cache("user:123", {"name": "John"}, ttl=3600)
        """
        try:
            client = self.get_client()

            if serializer == "json":
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)

            if ttl is not None:
                await client.setex(key, ttl, serialized_value)
            else:
                await client.set(key, serialized_value)

            logger.debug(
                "Cache value set",
                extra={
                    "key": key,
                    "ttl": ttl,
                    "serializer": serializer,
                },
            )

            return True

        except RedisError as e:
            logger.error(
                "Failed to set cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error setting cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def get_cache(
        self, key: str, default: Any = None, serializer: str = "json"
    ) -> Any:
        """
        Get cache value with optional default.

        Args:
            key: Cache key
            default: Default value if key not found
            serializer: Serialization format ("json" or "str")

        Returns:
            Cached value or default

        Example:
            >>> user_data = await redis_manager.get_cache("user:123", default={})
        """
        try:
            client = self.get_client()
            value = await client.get(key)

            if value is None:
                logger.debug(
                    "Cache miss",
                    extra={"key": key},
                )
                return default

            if serializer == "json":
                deserialized_value = json.loads(value)
            else:
                deserialized_value = value

            logger.debug(
                "Cache hit",
                extra={
                    "key": key,
                    "serializer": serializer,
                },
            )

            return deserialized_value

        except RedisError as e:
            logger.error(
                "Failed to get cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return default
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to deserialize cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "serializer": serializer,
                },
            )
            return default
        except Exception as e:
            logger.error(
                "Unexpected error getting cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return default

    async def delete_cache(self, key: str) -> bool:
        """
        Delete cache value by key.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise

        Example:
            >>> await redis_manager.delete_cache("user:123")
        """
        try:
            client = self.get_client()
            result = await client.delete(key)

            logger.debug(
                "Cache value deleted",
                extra={
                    "key": key,
                    "existed": result > 0,
                },
            )

            return result > 0

        except RedisError as e:
            logger.error(
                "Failed to delete cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error deleting cache value",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if cache key exists.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise

        Example:
            >>> exists = await redis_manager.exists("user:123")
        """
        try:
            client = self.get_client()
            result = await client.exists(key)

            logger.debug(
                "Cache key existence checked",
                extra={
                    "key": key,
                    "exists": result > 0,
                },
            )

            return result > 0

        except RedisError as e:
            logger.error(
                "Failed to check cache key existence",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error checking cache key existence",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted

        Example:
            >>> deleted = await redis_manager.clear_pattern("session:*")
        """
        try:
            client = self.get_client()
            keys = []

            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info(
                    "Cache keys deleted by pattern",
                    extra={
                        "pattern": pattern,
                        "deleted_count": deleted,
                    },
                )
                return deleted

            logger.debug(
                "No cache keys found matching pattern",
                extra={"pattern": pattern},
            )

            return 0

        except RedisError as e:
            logger.error(
                "Failed to clear cache keys by pattern",
                extra={
                    "pattern": pattern,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0
        except Exception as e:
            logger.error(
                "Unexpected error clearing cache keys by pattern",
                extra={
                    "pattern": pattern,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0

    async def close(self) -> None:
        """
        Close Redis client and cleanup resources.

        Should be called on application shutdown to properly close
        all Redis connections.
        """
        if self._client is not None:
            await self._client.close()
            logger.info("Redis client closed")
            self._client = None

        if self._pool is not None:
            await self._pool.disconnect()
            logger.info("Redis connection pool disconnected")
            self._pool = None


_redis_manager: RedisManager | None = None


def get_redis_manager() -> RedisManager:
    """
    Get global Redis manager instance.

    Creates and caches the Redis manager singleton.

    Returns:
        Redis manager instance
    """
    global _redis_manager

    if _redis_manager is None:
        settings = get_settings()
        _redis_manager = RedisManager(settings)
        logger.info("Redis manager initialized")

    return _redis_manager


async def get_redis_client() -> Redis:
    """
    FastAPI dependency for Redis client injection.

    Provides Redis client for FastAPI route handlers.

    Returns:
        Redis client instance

    Example:
        >>> @app.get("/cache/{key}")
        >>> async def get_cached(key: str, redis: Redis = Depends(get_redis_client)):
        ...     value = await redis.get(key)
        ...     return {"value": value}
    """
    redis_manager = get_redis_manager()
    return redis_manager.get_client()


async def check_redis_health() -> bool:
    """
    Check Redis health for monitoring and health check endpoints.

    Returns:
        True if Redis is healthy, False otherwise

    Example:
        >>> @app.get("/health/redis")
        >>> async def redis_health():
        ...     is_healthy = await check_redis_health()
        ...     if is_healthy:
        ...         return {"status": "healthy"}
        ...     raise HTTPException(status_code=503, detail="Redis unhealthy")
    """
    redis_manager = get_redis_manager()
    return await redis_manager.health_check()


async def close_redis_connections() -> None:
    """
    Close all Redis connections on application shutdown.

    Should be called in FastAPI lifespan or shutdown event.

    Example:
        >>> @app.on_event("shutdown")
        >>> async def shutdown():
        ...     await close_redis_connections()
    """
    global _redis_manager

    if _redis_manager is not None:
        await _redis_manager.close()
        _redis_manager = None
        logger.info("Redis connections closed")
