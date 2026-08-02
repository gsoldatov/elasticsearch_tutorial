from datetime import datetime, timezone

import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException
from tests.mocks.elastic_operations import ElasticOperations


async def test_update_nonexistent_blogpost_raises_not_found(
    elastic_service: ElasticService,
    data_generator,
):
    """Обновление несуществующего блогпоста — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найден"):
        await elastic_service.blogposts.update(
            "nonexistent", data_generator.blogposts.blogpost_update(),
        )


async def test_update_updated_at_is_set_to_now(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """updated_at обновляется на текущее время."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", [],
        updated_at="2025-01-01T00:00:00Z",
    )

    bp = await elastic_service.blogposts.update(
        "bp-1", data_generator.blogposts.blogpost_update(),
    )

    assert bp.updated_at is not None
    assert bp.updated_at != datetime(2025, 1, 1, tzinfo=timezone.utc)


async def test_update_preserves_updated_at_when_provided(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Если передан updated_at — используется переданное значение."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", [],
        updated_at="2025-01-01T00:00:00Z",
    )

    now = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    bp = await elastic_service.blogposts.update(
        "bp-1",
        data_generator.blogposts.blogpost_update(updated_at=now),
    )

    assert bp.updated_at == now


async def test_update_existing_blogpost(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Частичное обновление блогпоста."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Old Title", "Old Text", ["old"],
        updated_at="2025-01-01T00:00:00Z",
    )

    bp = await elastic_service.blogposts.update(
        "bp-1",
        data_generator.blogposts.blogpost_update(title="New Title", tags=["new"]),
    )

    assert bp.title == "New Title"
    assert bp.text == "Old Text"
    assert bp.tags == ["new"]
    assert bp.updated_at > datetime(2025, 1, 1, tzinfo=timezone.utc)
