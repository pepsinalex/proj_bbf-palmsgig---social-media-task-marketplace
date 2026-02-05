"""
Tests for SearchService.

Comprehensive tests for Elasticsearch-based task search operations,
including indexing, searching, updating, and bulk operations.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from elasticsearch import NotFoundError

from src.task_management.models.task import (
    PlatformEnum,
    Task,
    TaskStatusEnum,
    TaskTypeEnum,
)
from src.task_management.services.search_service import SearchService


@pytest.fixture
def mock_es_client() -> AsyncMock:
    """Create mock Elasticsearch client."""
    client = AsyncMock()
    client.indices = AsyncMock()
    client.indices.exists = AsyncMock(return_value=True)
    client.indices.create = AsyncMock()
    client.index = AsyncMock(return_value={"result": "created"})
    client.update = AsyncMock(return_value={"result": "updated"})
    client.delete = AsyncMock(return_value={"result": "deleted"})
    client.search = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def search_service(mock_es_client: AsyncMock) -> SearchService:
    """Create SearchService instance with mock client."""
    return SearchService(mock_es_client)


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    task = Task(
        id="task-123",
        creator_id="user-456",
        title="Like my Instagram post",
        description="Need 100 likes on my latest post about travel",
        instructions="1. Visit the post URL\n2. Click like\n3. Screenshot proof",
        platform=PlatformEnum.INSTAGRAM,
        task_type=TaskTypeEnum.LIKE,
        budget=Decimal("10.00"),
        service_fee=Decimal("1.50"),
        total_cost=Decimal("11.50"),
        max_performers=100,
        current_performers=0,
        status=TaskStatusEnum.ACTIVE,
        target_criteria={"countries": ["US", "CA"], "min_age": 18},
        expires_at=datetime.utcnow() + timedelta(days=7),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return task


class TestSearchServiceInitialization:
    """Tests for SearchService initialization."""

    def test_initialization_success(self, mock_es_client: AsyncMock) -> None:
        """Test successful SearchService initialization."""
        service = SearchService(mock_es_client)

        assert service.es_client == mock_es_client
        assert service.INDEX_NAME == "tasks"

    def test_index_name_constant(self, search_service: SearchService) -> None:
        """Test INDEX_NAME is set correctly."""
        assert search_service.INDEX_NAME == "tasks"

    def test_index_mapping_structure(self, search_service: SearchService) -> None:
        """Test INDEX_MAPPING has correct structure."""
        mapping = search_service.INDEX_MAPPING

        assert "mappings" in mapping
        assert "settings" in mapping
        assert "properties" in mapping["mappings"]

        properties = mapping["mappings"]["properties"]
        assert "task_id" in properties
        assert "title" in properties
        assert "description" in properties
        assert "platform" in properties
        assert "task_type" in properties
        assert "status" in properties
        assert "budget" in properties


class TestEnsureIndexExists:
    """Tests for ensure_index_exists method."""

    async def test_ensure_index_exists_when_exists(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test ensure_index_exists when index already exists."""
        mock_es_client.indices.exists.return_value = True

        await search_service.ensure_index_exists()

        mock_es_client.indices.exists.assert_called_once_with(index="tasks")
        mock_es_client.indices.create.assert_not_called()

    async def test_ensure_index_exists_creates_index(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test ensure_index_exists creates index when it doesn't exist."""
        mock_es_client.indices.exists.return_value = False

        await search_service.ensure_index_exists()

        mock_es_client.indices.exists.assert_called_once_with(index="tasks")
        mock_es_client.indices.create.assert_called_once_with(
            index="tasks", body=search_service.INDEX_MAPPING
        )

    async def test_ensure_index_exists_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test ensure_index_exists handles errors properly."""
        mock_es_client.indices.exists.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await search_service.ensure_index_exists()


class TestIndexTask:
    """Tests for index_task method."""

    async def test_index_task_success(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test successful task indexing."""
        mock_es_client.indices.exists.return_value = True

        result = await search_service.index_task(sample_task)

        assert result is True
        mock_es_client.index.assert_called_once()
        call_kwargs = mock_es_client.index.call_args[1]
        assert call_kwargs["index"] == "tasks"
        assert call_kwargs["id"] == sample_task.id
        assert call_kwargs["refresh"] is True

    async def test_index_task_document_structure(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test indexed document has correct structure."""
        mock_es_client.indices.exists.return_value = True

        await search_service.index_task(sample_task)

        call_kwargs = mock_es_client.index.call_args[1]
        document = call_kwargs["body"]

        assert document["task_id"] == sample_task.id
        assert document["title"] == sample_task.title
        assert document["description"] == sample_task.description
        assert document["platform"] == sample_task.platform.value
        assert document["task_type"] == sample_task.task_type.value
        assert document["status"] == sample_task.status.value
        assert document["budget"] == float(sample_task.budget)
        assert document["creator_id"] == sample_task.creator_id

    async def test_index_task_converts_decimals(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test task indexing converts Decimal fields to float."""
        mock_es_client.indices.exists.return_value = True

        await search_service.index_task(sample_task)

        call_kwargs = mock_es_client.index.call_args[1]
        document = call_kwargs["body"]

        assert isinstance(document["budget"], float)
        assert isinstance(document["service_fee"], float)
        assert isinstance(document["total_cost"], float)

    async def test_index_task_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test index_task handles indexing errors."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.index.side_effect = Exception("Indexing failed")

        with pytest.raises(Exception, match="Indexing failed"):
            await search_service.index_task(sample_task)

    async def test_index_task_ensures_index_exists(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test index_task ensures index exists before indexing."""
        mock_es_client.indices.exists.return_value = False

        await search_service.index_task(sample_task)

        mock_es_client.indices.create.assert_called_once()


class TestUpdateTaskIndex:
    """Tests for update_task_index method."""

    async def test_update_task_index_success(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test successful task index update."""
        mock_es_client.indices.exists.return_value = True

        result = await search_service.update_task_index(sample_task)

        assert result is True
        mock_es_client.update.assert_called_once()
        call_kwargs = mock_es_client.update.call_args[1]
        assert call_kwargs["index"] == "tasks"
        assert call_kwargs["id"] == sample_task.id
        assert call_kwargs["refresh"] is True

    async def test_update_task_index_uses_upsert(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test update_task_index uses doc_as_upsert."""
        mock_es_client.indices.exists.return_value = True

        await search_service.update_task_index(sample_task)

        call_kwargs = mock_es_client.update.call_args[1]
        body = call_kwargs["body"]

        assert "doc" in body
        assert "doc_as_upsert" in body
        assert body["doc_as_upsert"] is True

    async def test_update_task_index_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test update_task_index handles errors."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Update failed"):
            await search_service.update_task_index(sample_task)


class TestDeleteFromIndex:
    """Tests for delete_from_index method."""

    async def test_delete_from_index_success(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test successful task deletion from index."""
        task_id = "task-123"

        result = await search_service.delete_from_index(task_id)

        assert result is True
        mock_es_client.delete.assert_called_once_with(
            index="tasks", id=task_id, refresh=True
        )

    async def test_delete_from_index_not_found(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test delete_from_index returns False when task not found."""
        task_id = "task-999"
        mock_es_client.delete.side_effect = NotFoundError("Not found")

        result = await search_service.delete_from_index(task_id)

        assert result is False

    async def test_delete_from_index_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test delete_from_index handles other errors."""
        task_id = "task-123"
        mock_es_client.delete.side_effect = Exception("Delete failed")

        with pytest.raises(Exception, match="Delete failed"):
            await search_service.delete_from_index(task_id)


class TestSearchTasks:
    """Tests for search_tasks method."""

    async def test_search_tasks_basic_query(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test basic task search query."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.5,
                "hits": [
                    {
                        "_id": "task-123",
                        "_score": 1.5,
                        "_source": {
                            "task_id": "task-123",
                            "title": "Test task",
                            "status": "active",
                        },
                    }
                ],
            }
        }

        results = await search_service.search_tasks(query="test")

        assert results["total"] == 1
        assert len(results["hits"]) == 1
        assert results["hits"][0]["task_id"] == "task-123"
        assert results["hits"][0]["score"] == 1.5
        assert results["max_score"] == 1.5

    async def test_search_tasks_empty_query(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with empty query returns all tasks."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 5}, "max_score": None, "hits": []}
        }

        results = await search_service.search_tasks(query="")

        assert results["total"] == 5
        mock_es_client.search.assert_called_once()

    async def test_search_tasks_with_filters(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with filters."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        filters = {"status": "active", "platform": "instagram"}
        await search_service.search_tasks(query="test", filters=filters)

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]

        assert "filter" in search_body["query"]["bool"]
        filter_clauses = search_body["query"]["bool"]["filter"]
        assert len(filter_clauses) == 2

    async def test_search_tasks_with_list_filter(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with list-based filter."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        filters = {"platform": ["instagram", "facebook"]}
        await search_service.search_tasks(query="test", filters=filters)

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]
        filter_clauses = search_body["query"]["bool"]["filter"]

        assert any("terms" in clause for clause in filter_clauses)

    async def test_search_tasks_with_fuzzy(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with fuzzy matching enabled."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        await search_service.search_tasks(query="test", fuzzy=True)

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]
        multi_match = search_body["query"]["bool"]["must"][0]["multi_match"]

        assert "fuzziness" in multi_match
        assert multi_match["fuzziness"] == "AUTO"

    async def test_search_tasks_without_fuzzy(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with fuzzy matching disabled."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        await search_service.search_tasks(query="test", fuzzy=False)

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]
        multi_match = search_body["query"]["bool"]["must"][0]["multi_match"]

        assert "fuzziness" not in multi_match

    async def test_search_tasks_with_pagination(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with pagination parameters."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 100}, "max_score": None, "hits": []}
        }

        await search_service.search_tasks(query="test", size=10, from_=20)

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]

        assert search_body["size"] == 10
        assert search_body["from"] == 20

    async def test_search_tasks_with_custom_boost(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search with custom field boosting."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        await search_service.search_tasks(
            query="test",
            boost_title=5.0,
            boost_description=2.0,
            boost_instructions=0.5,
        )

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]
        multi_match = search_body["query"]["bool"]["must"][0]["multi_match"]
        fields = multi_match["fields"]

        assert "title^5.0" in fields
        assert "description^2.0" in fields
        assert "instructions^0.5" in fields

    async def test_search_tasks_sorting(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search results are sorted correctly."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.return_value = {
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        }

        await search_service.search_tasks(query="test")

        call_kwargs = mock_es_client.search.call_args[1]
        search_body = call_kwargs["body"]

        assert "sort" in search_body
        assert {"_score": {"order": "desc"}} in search_body["sort"]
        assert {"created_at": {"order": "desc"}} in search_body["sort"]

    async def test_search_tasks_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test search_tasks handles search errors."""
        mock_es_client.indices.exists.return_value = True
        mock_es_client.search.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="Search failed"):
            await search_service.search_tasks(query="test")


class TestBulkIndexTasks:
    """Tests for bulk_index_tasks method."""

    async def test_bulk_index_tasks_success(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test successful bulk indexing of tasks."""
        mock_es_client.indices.exists.return_value = True

        tasks = [sample_task]

        with patch(
            "src.task_management.services.search_service.async_bulk",
            return_value=(1, []),
        ) as mock_bulk:
            result = await search_service.bulk_index_tasks(tasks)

            assert result["success"] == 1
            assert result["errors"] == 0
            mock_bulk.assert_called_once()

    async def test_bulk_index_tasks_with_errors(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test bulk indexing with some errors."""
        mock_es_client.indices.exists.return_value = True

        tasks = [sample_task, sample_task]

        with patch(
            "src.task_management.services.search_service.async_bulk",
            return_value=(1, [{"error": "failed"}]),
        ) as mock_bulk:
            result = await search_service.bulk_index_tasks(tasks)

            assert result["success"] == 1
            assert result["errors"] == 1

    async def test_bulk_index_tasks_action_structure(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test bulk index actions have correct structure."""
        mock_es_client.indices.exists.return_value = True

        tasks = [sample_task]

        with patch(
            "src.task_management.services.search_service.async_bulk",
            return_value=(1, []),
        ) as mock_bulk:
            await search_service.bulk_index_tasks(tasks)

            call_args = mock_bulk.call_args[0]
            actions = call_args[1]

            assert len(actions) == 1
            assert actions[0]["_index"] == "tasks"
            assert actions[0]["_id"] == sample_task.id
            assert "_source" in actions[0]

    async def test_bulk_index_tasks_empty_list(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test bulk indexing with empty task list."""
        mock_es_client.indices.exists.return_value = True

        with patch(
            "src.task_management.services.search_service.async_bulk",
            return_value=(0, []),
        ):
            result = await search_service.bulk_index_tasks([])

            assert result["success"] == 0
            assert result["errors"] == 0

    async def test_bulk_index_tasks_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock, sample_task: Task
    ) -> None:
        """Test bulk_index_tasks handles errors."""
        mock_es_client.indices.exists.return_value = True

        tasks = [sample_task]

        with patch(
            "src.task_management.services.search_service.async_bulk",
            side_effect=Exception("Bulk operation failed"),
        ):
            with pytest.raises(Exception, match="Bulk operation failed"):
                await search_service.bulk_index_tasks(tasks)


class TestTaskToDocument:
    """Tests for _task_to_document method."""

    def test_task_to_document_structure(
        self, search_service: SearchService, sample_task: Task
    ) -> None:
        """Test _task_to_document creates correct structure."""
        document = search_service._task_to_document(sample_task)

        assert document["task_id"] == sample_task.id
        assert document["title"] == sample_task.title
        assert document["description"] == sample_task.description
        assert document["instructions"] == sample_task.instructions
        assert document["platform"] == sample_task.platform.value
        assert document["task_type"] == sample_task.task_type.value
        assert document["status"] == sample_task.status.value
        assert document["creator_id"] == sample_task.creator_id
        assert document["max_performers"] == sample_task.max_performers
        assert document["current_performers"] == sample_task.current_performers
        assert document["target_criteria"] == sample_task.target_criteria

    def test_task_to_document_converts_decimals(
        self, search_service: SearchService, sample_task: Task
    ) -> None:
        """Test _task_to_document converts Decimal to float."""
        document = search_service._task_to_document(sample_task)

        assert isinstance(document["budget"], float)
        assert isinstance(document["service_fee"], float)
        assert isinstance(document["total_cost"], float)
        assert document["budget"] == 10.0
        assert document["service_fee"] == 1.5
        assert document["total_cost"] == 11.5

    def test_task_to_document_converts_datetimes(
        self, search_service: SearchService, sample_task: Task
    ) -> None:
        """Test _task_to_document converts datetime to ISO format."""
        document = search_service._task_to_document(sample_task)

        assert isinstance(document["created_at"], str)
        assert isinstance(document["updated_at"], str)
        assert "T" in document["created_at"]

    def test_task_to_document_handles_none_expires_at(
        self, search_service: SearchService, sample_task: Task
    ) -> None:
        """Test _task_to_document handles None expires_at."""
        sample_task.expires_at = None

        document = search_service._task_to_document(sample_task)

        assert document["expires_at"] is None


class TestClose:
    """Tests for close method."""

    async def test_close_success(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test successful client close."""
        await search_service.close()

        mock_es_client.close.assert_called_once()

    async def test_close_handles_error(
        self, search_service: SearchService, mock_es_client: AsyncMock
    ) -> None:
        """Test close handles errors gracefully."""
        mock_es_client.close.side_effect = Exception("Close failed")

        # Should not raise exception
        await search_service.close()

        mock_es_client.close.assert_called_once()
