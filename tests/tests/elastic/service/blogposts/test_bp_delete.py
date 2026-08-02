import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException
from tests.mocks.elastic_operations import ElasticOperations


async def test_delete_nonexistent_blogpost_does_not_raise(
    elastic_service: ElasticService,
):
    """Удаление несуществующего блогпоста — не ошибка."""
    await elastic_service.blogposts.delete("nonexistent")


async def test_delete_existing_blogpost(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Удаление существующего блогпоста."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", [],
        updated_at="2025-01-01T00:00:00Z",
    )
    assert elastic_operations.blogposts.count() == 1

    await elastic_service.blogposts.delete("bp-1")

    assert elastic_operations.blogposts.count() == 0
    with pytest.raises(NotFoundException, match="не найден"):
        await elastic_service.blogposts.get("bp-1")
