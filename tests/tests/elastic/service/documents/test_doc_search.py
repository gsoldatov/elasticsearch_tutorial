import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


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
