from datetime import datetime, timezone

import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException
from tests.mocks.elastic_operations import ElasticOperations


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_search_empty_index_returns_not_found(
    elastic_service: ElasticService,
):
    """Поиск по пустому индексу — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найдены"):
        await elastic_service.blogposts.search("запрос")


# ── базовый поиск ──────────────────────────────────────────────────────────


async def test_search_finds_by_title(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск находит документ по совпадению в title."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Python и асинхронность", "Какой-то текст", ["python"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-2", "Готовим пиццу", "Рецепт теста", ["food"],
        updated_at="2025-01-02T00:00:00Z",
    )

    result = await elastic_service.blogposts.search("Python")
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].id == "bp-1"


async def test_search_finds_by_text(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск находит документ по совпадению в text."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Заголовок", "fastapi — это современный веб-фреймворк", ["python"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-2", "Другой пост", "Ничего общего", ["other"],
        updated_at="2025-01-02T00:00:00Z",
    )

    result = await elastic_service.blogposts.search("fastapi")
    assert result.total == 1
    assert result.items[0].id == "bp-1"


async def test_search_title_boosted_over_text(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """title^3 даёт буст: совпадение в title выше, чем в text."""
    elastic_operations.blogposts.index_blogpost(
        "bp-text", "Обычный заголовок", "elasticsearch — мощный поисковый движок", ["search"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-title", "elasticsearch для начинающих", "Какой-то текст", ["search"],
        updated_at="2025-01-02T00:00:00Z",
    )

    result = await elastic_service.blogposts.search("elasticsearch")
    assert result.total == 2
    # Документ с elasticsearch в title должен быть первым (выше score)
    assert result.items[0].id == "bp-title"
    assert result.items[1].id == "bp-text"


async def test_search_fuzziness_handles_typo(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """fuzziness: AUTO исправляет опечатки в поисковом запросе."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Elasticsearch tutorial", "Полное руководство", ["elastic"],
        updated_at="2025-01-01T00:00:00Z",
    )

    # Опечатка: "elasticsearch" → "elasticseerch"
    result = await elastic_service.blogposts.search("elasticseerch")
    assert result.total >= 1
    assert result.items[0].id == "bp-1"


# ── фильтры ────────────────────────────────────────────────────────────────


async def test_search_filter_by_min_time(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """min_time отсекает документы с updated_at раньше указанного."""
    elastic_operations.blogposts.index_blogpost(
        "old", "Старый пост", "Текст", ["a"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "new", "Новый пост", "Текст", ["a"],
        updated_at="2025-06-15T00:00:00Z",
    )

    cutoff = datetime(2025, 3, 1, tzinfo=timezone.utc)
    result = await elastic_service.blogposts.search("Текст", min_time=cutoff)
    assert result.total == 1
    assert result.items[0].id == "new"


async def test_search_filter_by_max_time(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """max_time отсекает документы с updated_at позже указанного."""
    elastic_operations.blogposts.index_blogpost(
        "old", "Старый пост", "Текст", ["a"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "new", "Новый пост", "Текст", ["a"],
        updated_at="2025-06-15T00:00:00Z",
    )

    cutoff = datetime(2025, 3, 1, tzinfo=timezone.utc)
    result = await elastic_service.blogposts.search("Текст", max_time=cutoff)
    assert result.total == 1
    assert result.items[0].id == "old"


async def test_search_filter_by_min_and_max_time(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """min_time + max_time вместе — только документы внутри диапазона."""
    elastic_operations.blogposts.index_blogpost(
        "old", "Старый пост", "Текст", ["a"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "mid", "Средний пост", "Текст", ["a"],
        updated_at="2025-03-15T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "new", "Новый пост", "Текст", ["a"],
        updated_at="2025-06-01T00:00:00Z",
    )

    min_t = datetime(2025, 2, 1, tzinfo=timezone.utc)
    max_t = datetime(2025, 5, 1, tzinfo=timezone.utc)
    result = await elastic_service.blogposts.search(
        "Текст", min_time=min_t, max_time=max_t,
    )
    assert result.total == 1
    assert result.items[0].id == "mid"


async def test_search_filter_by_tags(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Теги: хотя бы один должен совпасть (minimum_should_match: 1)."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Post 1", "Text", ["python", "fastapi"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-2", "Post 2", "Text", ["python", "django"],
        updated_at="2025-01-02T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-3", "Post 3", "Text", ["javascript"],
        updated_at="2025-01-03T00:00:00Z",
    )

    result = await elastic_service.blogposts.search("Post", tags=["fastapi"])
    assert result.total == 1
    assert result.items[0].id == "bp-1"


# ── пагинация ──────────────────────────────────────────────────────────────


async def test_search_pagination(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Пагинация: p=2 возвращает вторую страницу."""
    for i in range(5):
        elastic_operations.blogposts.index_blogpost(
            f"bp-{i + 1}", f"Post {i + 1}", "общий текст", ["a"],
            updated_at=f"2025-01-0{i + 1}T00:00:00Z",
        )

    # per_page=2 → страница 1: bp-5, bp-4; страница 2: bp-3, bp-2
    result = await elastic_service.blogposts.search(
        "общий текст", page=2, per_page=2,
    )
    assert result.total == 5
    assert len(result.items) == 2
    assert result.items[0].id == "bp-3"


async def test_search_per_page_limits_results(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """per_page ограничивает количество возвращаемых результатов."""
    for i in range(5):
        elastic_operations.blogposts.index_blogpost(
            f"bp-{i + 1}", f"Post {i + 1}", "общий текст", ["a"],
            updated_at=f"2025-01-0{i + 1}T00:00:00Z",
        )

    result = await elastic_service.blogposts.search("общий текст", per_page=3)
    assert result.total == 5
    assert len(result.items) == 3


# ── сортировка ─────────────────────────────────────────────────────────────


async def test_search_results_sorted_by_updated_at_desc(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Результаты поиска сортируются по updated_at по убыванию."""
    elastic_operations.blogposts.index_blogpost(
        "bp-old", "Старый пост", "текст", ["a"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-mid", "Средний пост", "текст", ["a"],
        updated_at="2025-03-15T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-new", "Новый пост", "текст", ["a"],
        updated_at="2025-06-01T00:00:00Z",
    )

    result = await elastic_service.blogposts.search("текст")

    assert result.total == 3
    assert len(result.items) == 3
    # Порядок по убыванию updated_at: новый → средний → старый
    assert result.items[0].id == "bp-new"
    assert result.items[1].id == "bp-mid"
    assert result.items[2].id == "bp-old"
