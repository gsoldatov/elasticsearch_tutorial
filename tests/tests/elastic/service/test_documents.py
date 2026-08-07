"""Тесты ElasticDocumentsService."""

import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


# ══════════════════════════════════════════════════════════════════════════════
# delete
# ══════════════════════════════════════════════════════════════════════════════


async def test_delete_on_nonexistent_index_raises(
    test_config: Config,
):
    """Удаление до создания индекса — ошибка (индекс не существует)."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": "nonexistent_index_name",
    })
    es = ElasticService(cfg)
    try:
        with pytest.raises(NotFoundError):
            await es.documents.delete(1)
    finally:
        await es.close()


async def test_delete_nonexistent_document_does_not_raise(
    elastic_service: ElasticService,
):
    """Удаление несуществующего документа — не падает (404 игнорируется)."""
    await elastic_service.documents.delete(99999)


async def test_delete_removes_document(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Удаление документа убирает его из результатов поиска."""
    elastic_operations.documents.index_document(1, "документ для удаления")

    result = await elastic_service.documents.search("удаления")
    assert result == [1]

    await elastic_service.documents.delete(1)

    result = await elastic_service.documents.search("удаления")
    assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# index_documents
# ══════════════════════════════════════════════════════════════════════════════


async def test_index_duplicate_id_overwrites(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Повторная индексация с тем же id перезаписывает документ."""
    await elastic_service.documents.index_documents([
        data_generator.documents.document(id=1, text="первая версия текста"),
    ])
    await elastic_service.documents.index_documents([
        data_generator.documents.document(id=1, text="вторая версия текста"),
    ])

    result_first = await elastic_service.documents.search("первая")
    assert result_first == []

    result_second = await elastic_service.documents.search("вторая")
    assert result_second == [1]


async def test_index_documents_bulk(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Массовая индексация: все документы попадают в индекс."""
    docs = [
        data_generator.documents.document(id=i, text=f"документ номер {i}")
        for i in range(50)
    ]
    await elastic_service.documents.index_documents(docs)

    result = await elastic_service.documents.search("документ номер 7")
    assert result == [7]


# ══════════════════════════════════════════════════════════════════════════════
# search
# ══════════════════════════════════════════════════════════════════════════════


async def test_search_on_nonexistent_index_raises(
    test_config: Config,
):
    """Поиск по несуществующему индексу — ошибка."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": "nonexistent_index_name",
    })
    es = ElasticService(cfg)
    try:
        with pytest.raises(NotFoundError):
            await es.documents.search("запрос")
    finally:
        await es.close()


async def test_search_empty_index_returns_empty_list(
    elastic_service: ElasticService,
):
    """Поиск по пустому индексу возвращает пустой список."""
    result = await elastic_service.documents.search("запрос")
    assert result == []


async def test_search_match_phrase_exact_ordering(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """match_phrase требует точного порядка слов."""
    elastic_operations.documents.index_document(1, "быстрая коричневая лиса")

    result = await elastic_service.documents.search("коричневая лиса")
    assert result == [1]

    result = await elastic_service.documents.search("лиса коричневая")
    assert result == []


async def test_search_finds_indexed_document(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
):
    """Поиск находит проиндексированный документ."""
    elastic_operations.documents.index_document(1, "пример текста для поиска")
    elastic_operations.documents.index_document(2, "другой документ")

    result = await elastic_service.documents.search("поиска")
    assert result == [1]
