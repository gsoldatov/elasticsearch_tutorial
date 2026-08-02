from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


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
