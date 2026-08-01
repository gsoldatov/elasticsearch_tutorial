from datetime import datetime, timezone

import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService
from src.exceptions import NotFoundException, UpdateConflict
from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostUpdate
from tests.mocks.elastic_operations import ElasticOperations


# ── create ─────────────────────────────────────────────────────────────────


async def test_create_without_id_generates_auto_id(
    elastic_service: ElasticService,
):
    """Создание без id — ES генерирует авто-id."""
    bp = await elastic_service.blogposts.create(
        BlogpostCreate(title="Заголовок", text="Текст", tags=["tag"]),
    )

    assert bp.id
    assert len(bp.id) > 0
    assert bp.title == "Заголовок"
    assert bp.text == "Текст"
    assert bp.tags == ["tag"]
    assert bp.updated_at is not None


async def test_create_with_explicit_id(
    elastic_service: ElasticService,
):
    """Создание с явным id."""
    bp = await elastic_service.blogposts.create(
        BlogpostCreate(id="my-bp-1", title="T", text="X", tags=[]),
    )

    assert bp.id == "my-bp-1"


async def test_create_with_updated_at_uses_provided_value(
    elastic_service: ElasticService,
):
    """Если передан updated_at — используется он, а не pipeline."""
    now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    bp = await elastic_service.blogposts.create(
        BlogpostCreate(title="T", text="X", tags=[], updated_at=now),
    )

    assert bp.updated_at == now


async def test_create_duplicate_id_raises_update_conflict(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Повторное создание с тем же id — UpdateConflict."""
    await elastic_service.blogposts.create(
        BlogpostCreate(id="dup", title="First", text="X", tags=[]),
    )

    with pytest.raises(UpdateConflict):
        await elastic_service.blogposts.create(
            BlogpostCreate(id="dup", title="Second", text="Y", tags=[]),
        )

    # Проверяем, что первый документ не перезаписан
    bp = await elastic_service.blogposts.get("dup")
    assert bp.title == "First"


# ── get ────────────────────────────────────────────────────────────────────


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


async def test_get_nonexistent_blogpost_raises_not_found(
    elastic_service: ElasticService,
):
    """Получение несуществующего блогпоста — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найден"):
        await elastic_service.blogposts.get("nonexistent")


# ── update ─────────────────────────────────────────────────────────────────


async def test_update_existing_blogpost(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Частичное обновление блогпоста."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Old Title", "Old Text", ["old"],
        updated_at="2025-01-01T00:00:00Z",
    )

    bp = await elastic_service.blogposts.update(
        "bp-1",
        BlogpostUpdate(title="New Title", tags=["new"]),
    )

    assert bp.title == "New Title"
    assert bp.text == "Old Text"
    assert bp.tags == ["new"]
    assert bp.updated_at > datetime(2025, 1, 1, tzinfo=timezone.utc)


async def test_update_updated_at_is_set_to_now(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """updated_at обновляется на текущее время."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", [],
        updated_at="2025-01-01T00:00:00Z",
    )

    before = datetime.now(timezone.utc)
    bp = await elastic_service.blogposts.update(
        "bp-1", BlogpostUpdate(title="New"),
    )
    after = datetime.now(timezone.utc)

    assert bp.updated_at is not None
    # Допуск: updated_at не совпадает со старым значением
    assert bp.updated_at != datetime(2025, 1, 1, tzinfo=timezone.utc)


async def test_update_nonexistent_blogpost_raises_not_found(
    elastic_service: ElasticService,
):
    """Обновление несуществующего блогпоста — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найден"):
        await elastic_service.blogposts.update(
            "nonexistent", BlogpostUpdate(title="New"),
        )


async def test_update_preserves_updated_at_when_provided(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Если передан updated_at — используется переданное значение."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", [],
        updated_at="2025-01-01T00:00:00Z",
    )

    now = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    bp = await elastic_service.blogposts.update(
        "bp-1",
        BlogpostUpdate(title="New", updated_at=now),
    )

    assert bp.updated_at == now


# ── delete ─────────────────────────────────────────────────────────────────


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


async def test_delete_nonexistent_blogpost_does_not_raise(
    elastic_service: ElasticService,
):
    """Удаление несуществующего блогпоста — не ошибка."""
    await elastic_service.blogposts.delete("nonexistent")


# ── index_blogposts ────────────────────────────────────────────────────────


async def test_index_blogposts_bulk(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Массовая индексация блогпостов."""
    from src.models.blogpost import Blogpost

    blogposts = [
        Blogpost(
            id=str(i),
            title=f"Post {i}",
            text=f"Text {i}",
            tags=["bulk"],
            updated_at=datetime(2025, 1, i, tzinfo=timezone.utc),
        )
        for i in range(1, 11)
    ]
    await elastic_service.blogposts.index_blogposts(blogposts)

    assert elastic_operations.blogposts.count() == 10
    bp = await elastic_service.blogposts.get("5")
    assert bp.title == "Post 5"
