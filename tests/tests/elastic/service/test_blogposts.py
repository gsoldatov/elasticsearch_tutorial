"""Тесты ElasticBlogpostsService."""

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException, UpdateConflict
from src.models.blogpost import BlogpostTextChunk
from tests.mocks.elastic_mock import BlogpostsEmbeddingsMock
from tests.mocks.elastic_operations import ElasticOperations


# ══════════════════════════════════════════════════════════════════════════════
# fixtures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def mock_blogposts_embeddings(
    elastic_service: ElasticService,
) -> AsyncGenerator[BlogpostsEmbeddingsMock, None]:
    """Подменяет embeddings на замоканную версию.

    Возвращает BlogpostsEmbeddingsMock — тест может настроить
    результат через set_result(blogpost_id, title_vector, chunks).
    """
    mock = BlogpostsEmbeddingsMock()
    orig = elastic_service.blogposts._embeddings
    elastic_service.blogposts._embeddings = mock
    try:
        yield mock
    finally:
        elastic_service.blogposts._embeddings = orig


# ══════════════════════════════════════════════════════════════════════════════
# create
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# delete
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# get
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# index_blogposts
# ══════════════════════════════════════════════════════════════════════════════


async def test_index_blogposts_bulk(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    mock_blogposts_embeddings: BlogpostsEmbeddingsMock,
    data_generator,
):
    """Массовая индексация блогпостов: title_vector добавляется в _source,
    чанки индексируются в отдельный индекс."""
    mock_vector = [0.1] * 384
    mock_chunks = [
        BlogpostTextChunk(
            blogpost_id="5",
            chunk_index=0,
            chunk_text="Text 5",
            chunk_vector=mock_vector,
        ),
        BlogpostTextChunk(
            blogpost_id="5",
            chunk_index=1,
            chunk_text="Text 5 продолжение",
            chunk_vector=mock_vector,
        ),
    ]

    # По умолчанию возвращаем вектор без чанков; для "5" — с чанками
    mock_blogposts_embeddings.set_result(
        "5", title_vector=mock_vector, chunks=mock_chunks,
    )
    for i in range(1, 11):
        if i != 5:
            mock_blogposts_embeddings.set_result(
                str(i), title_vector=mock_vector,
            )

    blogposts = [
        data_generator.blogposts.blogpost(
            id=str(i),
            title=f"Post {i}",
            text=f"Text {i}",
            tags=["bulk"],
            updated_at=datetime(2025, 1, i, tzinfo=timezone.utc),
        )
        for i in range(1, 11)
    ]
    await elastic_service.blogposts.index_blogposts(blogposts)

    # Документы в индексе блогпостов
    assert elastic_operations.blogposts.count() == 10
    bp = await elastic_service.blogposts.get("5")
    assert bp.title == "Post 5"

    # title_vector присутствует в _source
    raw = elastic_operations.blogposts.get_blogpost("5")
    assert raw is not None
    assert "title_vector" in raw
    assert len(raw["title_vector"]) == 384

    # Чанки в индексе чанков
    chunks_client = elastic_operations._client
    chunks_count = chunks_client.count(
        index=elastic_operations._config.es_blogposts_text_chunks_index_name,
    )
    assert chunks_count["count"] == 2

    # Проверка содержимого чанков
    chunks_resp = chunks_client.search(
        index=elastic_operations._config.es_blogposts_text_chunks_index_name,
        body={"query": {"match_all": {}}},
    )
    chunk_hits = chunks_resp["hits"]["hits"]
    assert len(chunk_hits) == 2
    chunk_ids = {h["_source"]["blogpost_id"] for h in chunk_hits}
    assert chunk_ids == {"5"}


# ══════════════════════════════════════════════════════════════════════════════
# search
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# search_tags
# ══════════════════════════════════════════════════════════════════════════════


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_search_tags_empty_index_returns_not_found(
    elastic_service: ElasticService,
):
    """Поиск по пустому индексу — NotFoundException."""
    with pytest.raises(NotFoundException, match="не найдены"):
        await elastic_service.blogposts.search_tags("python")


# ── базовый поиск ──────────────────────────────────────────────────────────


async def test_search_tags_prefix_match(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск по префиксу возвращает все теги матчящихся документов."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Post 1", "Text", ["python", "fastapi"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-2", "Post 2", "Text", ["pytest", "django"],
        updated_at="2025-01-02T00:00:00Z",
    )

    result = await elastic_service.blogposts.search_tags("py")
    assert result == ["pytest", "python"]


async def test_search_tags_case_insensitive(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск не зависит от регистра."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", ["Python"],
        updated_at="2025-01-01T00:00:00Z",
    )

    # Запрос в верхнем регистре находит тег в смешанном
    result = await elastic_service.blogposts.search_tags("PY")
    assert "Python" in result


async def test_search_tags_normalizes_query(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Пробелы заменяются на '_', не-букво-цифры удаляются."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", ["machine_learning"],
        updated_at="2025-01-01T00:00:00Z",
    )

    # "machine learning" → "machine_learning"
    result = await elastic_service.blogposts.search_tags("machine learning!?.")
    assert "machine_learning" in result


async def test_search_tags_no_match_returns_not_found(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Не-префиксный запрос возвращает 404."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "T", "X", ["python"],
        updated_at="2025-01-01T00:00:00Z",
    )

    # "qy" не является префиксом "python"
    with pytest.raises(NotFoundException, match="не найдены"):
        await elastic_service.blogposts.search_tags("qy")


async def test_search_tags_returns_unique_sorted(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Одинаковые теги из разных блогпостов возвращаются одним элементом
    и сортируются."""
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "A", "X", ["python", "fastapi"],
        updated_at="2025-01-01T00:00:00Z",
    )
    elastic_operations.blogposts.index_blogpost(
        "bp-2", "B", "X", ["python", "django"],
        updated_at="2025-01-02T00:00:00Z",
    )

    result = await elastic_service.blogposts.search_tags("p")
    assert result == ["python"]


# ── лимит результата — не более 10 тегов ───────────────────────────────────


async def test_search_tags_returns_at_most_10(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Если подходящих тегов больше 10, возвращаются только первые 10
    по алфавиту; неподходящие теги отфильтровываются."""
    py_tags = [f"py{i:02d}" for i in range(12)]
    non_matching = ["java", "rust", "go"]
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Post", "Text", py_tags + non_matching,
        updated_at="2025-01-01T00:00:00Z",
    )

    result = await elastic_service.blogposts.search_tags("py")
    assert len(result) == 10
    assert result == py_tags[:10]


async def test_search_tags_exactly_10(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Если подходящих тегов ровно 10 — возвращаются все;
    неподходящие теги отфильтровываются."""
    py_tags = [f"py{i:02d}" for i in range(10)]
    non_matching = ["java", "rust", "go"]
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Post", "Text", py_tags + non_matching,
        updated_at="2025-01-01T00:00:00Z",
    )

    result = await elastic_service.blogposts.search_tags("py")
    assert len(result) == 10
    assert result == py_tags


async def test_search_tags_fewer_than_10(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Если подходящих тегов меньше 10 — возвращаются все;
    неподходящие теги отфильтровываются."""
    py_tags = ["pya", "pyb", "pyc", "pyd", "pye"]
    non_matching = ["java", "rust", "go"]
    elastic_operations.blogposts.index_blogpost(
        "bp-1", "Post", "Text", py_tags + non_matching,
        updated_at="2025-01-01T00:00:00Z",
    )

    result = await elastic_service.blogposts.search_tags("py")
    assert len(result) == 5
    assert result == sorted(py_tags)


# ══════════════════════════════════════════════════════════════════════════════
# update
# ══════════════════════════════════════════════════════════════════════════════


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
