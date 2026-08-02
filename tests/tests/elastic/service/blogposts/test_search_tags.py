import pytest

from src.elastic import ElasticService
from src.exceptions import NotFoundException
from tests.mocks.elastic_operations import ElasticOperations


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
