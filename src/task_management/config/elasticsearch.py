"""
Elasticsearch Configuration and Client Management.

Provides Elasticsearch client initialization, connection management,
and index configuration for task search functionality.
"""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch

from src.shared.config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_elasticsearch_client(settings: Settings | None = None) -> AsyncElasticsearch:
    """
    Get configured Elasticsearch async client.

    Args:
        settings: Application settings (uses global settings if not provided)

    Returns:
        Configured AsyncElasticsearch client instance

    Raises:
        Exception: If client initialization fails
    """
    if settings is None:
        settings = get_settings()

    try:
        # Elasticsearch URL from environment (default to localhost for development)
        es_url = "http://localhost:9200"
        if hasattr(settings, "ELASTICSEARCH_URL") and settings.ELASTICSEARCH_URL:
            es_url = str(settings.ELASTICSEARCH_URL)

        client = AsyncElasticsearch(
            [es_url],
            verify_certs=settings.is_production(),
            max_retries=3,
            retry_on_timeout=True,
            request_timeout=30,
        )

        logger.info(
            "Elasticsearch client initialized",
            extra={
                "url": es_url,
                "environment": settings.ENVIRONMENT,
            },
        )

        return client

    except Exception as e:
        logger.error(
            "Failed to initialize Elasticsearch client",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise


async def check_elasticsearch_health() -> bool:
    """
    Check Elasticsearch cluster health.

    Returns:
        True if Elasticsearch is healthy, False otherwise
    """
    try:
        client = get_elasticsearch_client()
        health = await client.cluster.health()
        await client.close()

        status = health.get("status", "red")
        is_healthy = status in ["green", "yellow"]

        logger.info(
            "Elasticsearch health check completed",
            extra={"status": status, "is_healthy": is_healthy},
        )

        return is_healthy

    except Exception as e:
        logger.warning(
            "Elasticsearch health check failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False
