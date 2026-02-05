"""
Elasticsearch Search Service for Task Discovery.

Provides full-text search capabilities for tasks using Elasticsearch,
including indexing, searching, updating, and deleting task documents.
"""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from src.task_management.models.task import Task

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for Elasticsearch-based task search operations.

    Manages task indexing, search queries, and result ranking with
    comprehensive error handling and logging.
    """

    INDEX_NAME = "tasks"

    # Elasticsearch mapping for task documents
    INDEX_MAPPING = {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "description": {"type": "text", "analyzer": "standard"},
                "instructions": {"type": "text", "analyzer": "standard"},
                "platform": {"type": "keyword"},
                "task_type": {"type": "keyword"},
                "status": {"type": "keyword"},
                "budget": {"type": "float"},
                "service_fee": {"type": "float"},
                "total_cost": {"type": "float"},
                "max_performers": {"type": "integer"},
                "current_performers": {"type": "integer"},
                "creator_id": {"type": "keyword"},
                "target_criteria": {"type": "object", "enabled": True},
                "expires_at": {"type": "date"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "standard": {
                        "type": "standard",
                        "stopwords": "_english_",
                    }
                }
            },
        },
    }

    def __init__(self, es_client: AsyncElasticsearch) -> None:
        """
        Initialize SearchService with Elasticsearch client.

        Args:
            es_client: Configured AsyncElasticsearch client instance
        """
        self.es_client = es_client
        logger.info("SearchService initialized", extra={"index_name": self.INDEX_NAME})

    async def ensure_index_exists(self) -> None:
        """
        Ensure the task index exists, creating it if necessary.

        Creates the index with predefined mappings and settings if it doesn't exist.
        """
        try:
            exists = await self.es_client.indices.exists(index=self.INDEX_NAME)
            if not exists:
                logger.info(
                    "Creating Elasticsearch index",
                    extra={"index_name": self.INDEX_NAME},
                )
                await self.es_client.indices.create(
                    index=self.INDEX_NAME, body=self.INDEX_MAPPING
                )
                logger.info(
                    "Elasticsearch index created successfully",
                    extra={"index_name": self.INDEX_NAME},
                )
            else:
                logger.debug(
                    "Elasticsearch index already exists",
                    extra={"index_name": self.INDEX_NAME},
                )
        except Exception as e:
            logger.error(
                "Failed to ensure index exists",
                extra={
                    "index_name": self.INDEX_NAME,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def index_task(self, task: Task) -> bool:
        """
        Index a task document in Elasticsearch.

        Args:
            task: Task model instance to index

        Returns:
            True if indexing succeeded, False otherwise

        Raises:
            Exception: If indexing fails
        """
        try:
            await self.ensure_index_exists()

            document = self._task_to_document(task)

            response = await self.es_client.index(
                index=self.INDEX_NAME, id=task.id, body=document, refresh=True
            )

            logger.info(
                "Task indexed successfully",
                extra={
                    "task_id": task.id,
                    "index_name": self.INDEX_NAME,
                    "result": response.get("result"),
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to index task",
                extra={
                    "task_id": task.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def update_task_index(self, task: Task) -> bool:
        """
        Update an existing task document in Elasticsearch.

        Args:
            task: Task model instance with updated data

        Returns:
            True if update succeeded, False otherwise

        Raises:
            Exception: If update fails
        """
        try:
            await self.ensure_index_exists()

            document = self._task_to_document(task)

            response = await self.es_client.update(
                index=self.INDEX_NAME,
                id=task.id,
                body={"doc": document, "doc_as_upsert": True},
                refresh=True,
            )

            logger.info(
                "Task index updated successfully",
                extra={
                    "task_id": task.id,
                    "index_name": self.INDEX_NAME,
                    "result": response.get("result"),
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to update task index",
                extra={
                    "task_id": task.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def delete_from_index(self, task_id: str) -> bool:
        """
        Delete a task document from Elasticsearch.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if deletion succeeded, False if task not found

        Raises:
            Exception: If deletion fails
        """
        try:
            await self.es_client.delete(
                index=self.INDEX_NAME, id=task_id, refresh=True
            )

            logger.info(
                "Task deleted from index successfully",
                extra={"task_id": task_id, "index_name": self.INDEX_NAME},
            )
            return True

        except NotFoundError:
            logger.warning(
                "Task not found in index for deletion",
                extra={"task_id": task_id, "index_name": self.INDEX_NAME},
            )
            return False

        except Exception as e:
            logger.error(
                "Failed to delete task from index",
                extra={
                    "task_id": task_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def search_tasks(
        self,
        query: str,
        search_fields: list[str] | None = None,
        boost_title: float = 3.0,
        boost_description: float = 1.5,
        boost_instructions: float = 1.0,
        fuzzy: bool = True,
        filters: dict[str, Any] | None = None,
        size: int = 20,
        from_: int = 0,
    ) -> dict[str, Any]:
        """
        Search for tasks using full-text search.

        Args:
            query: Search query string
            search_fields: Fields to search in (defaults to all text fields)
            boost_title: Boost factor for title field
            boost_description: Boost factor for description field
            boost_instructions: Boost factor for instructions field
            fuzzy: Enable fuzzy matching for typo tolerance
            filters: Additional filters (status, platform, etc.)
            size: Number of results to return
            from_: Starting offset for pagination

        Returns:
            Dictionary with search results and metadata

        Raises:
            Exception: If search fails
        """
        try:
            await self.ensure_index_exists()

            if search_fields is None:
                search_fields = ["title", "description", "instructions"]

            # Build multi-match query with field boosting
            must_clauses = []

            if query:
                multi_match = {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            f"title^{boost_title}",
                            f"description^{boost_description}",
                            f"instructions^{boost_instructions}",
                        ],
                        "type": "best_fields",
                        "operator": "or",
                    }
                }

                if fuzzy:
                    multi_match["multi_match"]["fuzziness"] = "AUTO"

                must_clauses.append(multi_match)

            # Build filter clauses
            filter_clauses = []
            if filters:
                for field, value in filters.items():
                    if value is not None:
                        if isinstance(value, list):
                            filter_clauses.append({"terms": {field: value}})
                        else:
                            filter_clauses.append({"term": {field: value}})

            # Construct the search query
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses,
                    }
                },
                "from": from_,
                "size": size,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"created_at": {"order": "desc"}},
                ],
            }

            logger.debug(
                "Executing search query",
                extra={
                    "query": query,
                    "search_fields": search_fields,
                    "filters": filters,
                    "size": size,
                    "from": from_,
                },
            )

            response = await self.es_client.search(
                index=self.INDEX_NAME, body=search_body
            )

            results = {
                "total": response["hits"]["total"]["value"],
                "hits": [
                    {
                        "task_id": hit["_id"],
                        "score": hit["_score"],
                        "document": hit["_source"],
                    }
                    for hit in response["hits"]["hits"]
                ],
                "max_score": response["hits"]["max_score"],
            }

            logger.info(
                "Search completed successfully",
                extra={
                    "query": query,
                    "total_results": results["total"],
                    "returned_results": len(results["hits"]),
                    "max_score": results["max_score"],
                },
            )

            return results

        except Exception as e:
            logger.error(
                "Search query failed",
                extra={
                    "query": query,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    async def bulk_index_tasks(self, tasks: list[Task]) -> dict[str, int]:
        """
        Bulk index multiple tasks for performance.

        Args:
            tasks: List of Task model instances to index

        Returns:
            Dictionary with success and failure counts

        Raises:
            Exception: If bulk indexing fails
        """
        try:
            await self.ensure_index_exists()

            actions = [
                {
                    "_index": self.INDEX_NAME,
                    "_id": task.id,
                    "_source": self._task_to_document(task),
                }
                for task in tasks
            ]

            success_count, errors = await async_bulk(
                self.es_client, actions, raise_on_error=False
            )

            logger.info(
                "Bulk indexing completed",
                extra={
                    "total_tasks": len(tasks),
                    "success_count": success_count,
                    "error_count": len(errors),
                },
            )

            return {"success": success_count, "errors": len(errors)}

        except Exception as e:
            logger.error(
                "Bulk indexing failed",
                extra={
                    "task_count": len(tasks),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def _task_to_document(self, task: Task) -> dict[str, Any]:
        """
        Convert Task model to Elasticsearch document.

        Args:
            task: Task model instance

        Returns:
            Dictionary representing the Elasticsearch document
        """
        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "instructions": task.instructions,
            "platform": task.platform.value,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "budget": float(task.budget),
            "service_fee": float(task.service_fee),
            "total_cost": float(task.total_cost),
            "max_performers": task.max_performers,
            "current_performers": task.current_performers,
            "creator_id": task.creator_id,
            "target_criteria": task.target_criteria,
            "expires_at": task.expires_at.isoformat() if task.expires_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    async def close(self) -> None:
        """Close the Elasticsearch client connection."""
        try:
            await self.es_client.close()
            logger.info("Elasticsearch client closed successfully")
        except Exception as e:
            logger.error(
                "Failed to close Elasticsearch client",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
