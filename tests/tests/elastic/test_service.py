import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ── search ─────────────────────────────────────────────────────────────────


async def test_search_on_nonexistent_index_raises(
    real_elastic_service: ElasticService,
    test_config: Config,
):
    """Поиск по несуществующему индексу — ошибка."""
    saved = test_config.es_documents_index_name
    test_config.es_documents_index_name = "nonexistent_index_name"
    try:
        with pytest.raises(NotFoundError):
            await real_elastic_service.search("запрос")
    finally:
        test_config.es_documents_index_name = saved


async def test_search_empty_index_returns_empty_list(
    real_elastic_service: ElasticService,
):
    """Поиск по пустому индексу возвращает пустой список."""
    result = await real_elastic_service.search("запрос")
    assert result == []


async def test_search_match_phrase_exact_ordering(
    real_elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """match_phrase требует точного порядка слов."""
    elastic_operations.index_document(1, "быстрая коричневая лиса")

    result = await real_elastic_service.search("коричневая лиса")
    assert result == [1]

    result = await real_elastic_service.search("лиса коричневая")
    assert result == []


async def test_search_finds_indexed_document(
    real_elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск находит проиндексированный документ."""
    elastic_operations.index_document(1, "пример текста для поиска")
    elastic_operations.index_document(2, "другой документ")

    result = await real_elastic_service.search("поиска")
    assert result == [1]


# ── delete ─────────────────────────────────────────────────────────────────


async def test_delete_nonexistent_document_does_not_raise(
    real_elastic_service: ElasticService,
):
    """Удаление несуществующего документа — не падает (404 игнорируется)."""
    await real_elastic_service.delete(99999)


async def test_delete_on_nonexistent_index_raises(
    real_elastic_service: ElasticService,
    test_config: Config,
):
    """Удаление до создания индекса — ошибка (индекс не существует)."""
    saved = test_config.es_documents_index_name
    test_config.es_documents_index_name = "nonexistent_index_name"
    try:
        with pytest.raises(NotFoundError):
            await real_elastic_service.delete(1)
    finally:
        test_config.es_documents_index_name = saved


async def test_delete_removes_document(
    real_elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Удаление документа убирает его из результатов поиска."""
    elastic_operations.index_document(1, "документ для удаления")

    result = await real_elastic_service.search("удаления")
    assert result == [1]

    await real_elastic_service.delete(1)

    result = await real_elastic_service.search("удаления")
    assert result == []


# ── create_index / delete_index ────────────────────────────────────────────


async def test_create_and_delete_index_idempotent(
    real_elastic_service: ElasticService,
    test_config: Config,
    elastic_operations: ElasticOperations,
):
    """Повторный вызов create_index и delete_index не падает."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_idx"
    try:
        await real_elastic_service.create_index()
        await real_elastic_service.create_index()

        await real_elastic_service.delete_index()
        await real_elastic_service.delete_index()
    finally:
        elastic_operations.delete_index(idx)
        test_config.es_documents_index_name = saved


async def test_recreate_index_after_delete(
    real_elastic_service: ElasticService,
    test_config: Config,
    elastic_operations: ElasticOperations,
):
    """Индекс можно пересоздать после удаления."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_idx"
    try:
        await real_elastic_service.create_index()
        await real_elastic_service.delete_index()
        await real_elastic_service.create_index()

        await real_elastic_service.index_documents([
            {"id": 1, "text": "новый документ"},
        ])
        result = await real_elastic_service.search("документ")
        assert result == [1]
    finally:
        elastic_operations.delete_index(idx)
        test_config.es_documents_index_name = saved


# ── index_documents ────────────────────────────────────────────────────────


async def test_index_documents_bulk(
    real_elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Массовая индексация: все документы попадают в индекс."""
    docs = [{"id": i, "text": f"документ номер {i}"} for i in range(50)]
    await real_elastic_service.index_documents(docs)

    result = await real_elastic_service.search("документ номер 7")
    assert result == [7]


async def test_index_duplicate_id_overwrites(
    real_elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Повторная индексация с тем же id перезаписывает документ."""
    await real_elastic_service.index_documents([
        {"id": 1, "text": "первая версия текста"},
    ])
    await real_elastic_service.index_documents([
        {"id": 1, "text": "вторая версия текста"},
    ])

    result_first = await real_elastic_service.search("первая")
    assert result_first == []

    result_second = await real_elastic_service.search("вторая")
    assert result_second == [1]
