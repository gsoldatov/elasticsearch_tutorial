from datetime import datetime, timezone

import pytest

from src.elastic import ElasticService
from src.exceptions import UpdateConflict
from tests.mocks.elastic_operations import ElasticOperations


async def test_create_duplicate_id_raises_update_conflict(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Повторное создание с тем же id — UpdateConflict."""
    await elastic_service.blogposts.create(
        data_generator.blogposts.blogpost_create(id="dup", title="First"),
    )

    with pytest.raises(UpdateConflict):
        await elastic_service.blogposts.create(
            data_generator.blogposts.blogpost_create(id="dup", title="Second"),
        )

    # Проверяем, что первый документ не перезаписан
    bp = await elastic_service.blogposts.get("dup")
    assert bp.title == "First"


async def test_create_with_updated_at_uses_provided_value(
    elastic_service: ElasticService,
    data_generator,
):
    """Если передан updated_at — используется он, а не pipeline."""
    now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    bp = await elastic_service.blogposts.create(
        data_generator.blogposts.blogpost_create(updated_at=now),
    )

    assert bp.updated_at == now


async def test_create_without_id_generates_auto_id(
    elastic_service: ElasticService,
    data_generator,
):
    """Создание без id — ES генерирует авто-id."""
    bp = await elastic_service.blogposts.create(
        data_generator.blogposts.blogpost_create(title="Заголовок", text="Текст", tags=["tag"]),
    )

    assert bp.id
    assert len(bp.id) > 0
    assert bp.title == "Заголовок"
    assert bp.text == "Текст"
    assert bp.tags == ["tag"]
    assert bp.updated_at is not None


async def test_create_with_explicit_id(
    elastic_service: ElasticService,
    data_generator,
):
    """Создание с явным id."""
    bp = await elastic_service.blogposts.create(
        data_generator.blogposts.blogpost_create(id="my-bp-1", title="T", text="X", tags=[]),
    )

    assert bp.id == "my-bp-1"
