import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


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
