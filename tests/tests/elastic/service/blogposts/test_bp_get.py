from datetime import datetime, timezone

import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException
from tests.mocks.elastic_operations import ElasticOperations


async def test_get_nonexistent_blogpost_raises_not_found(
    elastic_service: ElasticService,
):
    """Получение несуществующего блогпоста — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найден"):
        await elastic_service.blogposts.get("nonexistent")


async def test_get_existing_blogpost(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Получение существующего блогпоста."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Заголовок", "Текст", ["a", "b"],
        updated_at="2025-01-01T00:00:00Z",
    )

    bp = await elastic_service.blogposts.get("bp-1")
    assert bp.id == "bp-1"
    assert bp.title == "Заголовок"
    assert bp.text == "Текст"
    assert bp.tags == ["a", "b"]
    assert bp.updated_at == datetime(2025, 1, 1, tzinfo=timezone.utc)
