from unittest.mock import patch

from elasticsearch import ConnectionError
from sqlalchemy.exc import OperationalError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_search_missing_query_param_returns_422(test_client):
    """Отсутствует параметр q — 422."""
    response = await test_client.get("/search")
    assert response.status_code == 422


async def test_search_empty_query_param_returns_422(test_client):
    """Параметр q пустой — 422 (min_length=1)."""
    response = await test_client.get("/search", params={"q": ""})
    assert response.status_code == 422


async def test_search_db_operational_error_returns_503(test_client, elastic_mock):
    """Ошибка соединения с БД — 503."""
    elastic_mock.set_search_result("test", [1])
    with patch(
        "src.db.repository.document.DocumentRepository.get_by_ids",
        side_effect=OperationalError("connection refused", None, None),
    ):
        response = await test_client.get("/search", params={"q": "test"})
        assert response.status_code == 503
        assert response.json()["detail"] == "Сервис недоступен"


async def test_search_es_error_returns_503(test_client, elastic_mock):
    """Ошибка Elasticsearch — 503."""
    elastic_mock.raise_on_search = ConnectionError("cluster down")
    response = await test_client.get("/search", params={"q": "test"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_search_returns_404_when_es_returns_nothing(test_client):
    """ES не нашёл совпадений — 404."""
    response = await test_client.get("/search", params={"q": "nothing"})
    assert response.status_code == 404
    assert "Документы по заданному запросу не найдены" in response.json()["detail"]


async def test_search_returns_404_when_docs_not_in_db(test_client, elastic_mock):
    """ES вернул id, но документов с такими id нет в БД — 404."""
    elastic_mock.set_search_result("missing", [99999])
    response = await test_client.get("/search", params={"q": "missing"})
    assert response.status_code == 404


# ── корректные ─────────────────────────────────────────────────────────────


async def test_search_results_sorted_by_created_date_desc(
    test_client, db_operations, data_generator, elastic_mock,
):
    """Результаты упорядочены по created_date DESC."""
    dates = ["2025-01-01 00:00:00", "2025-06-15 00:00:00", "2025-03-10 00:00:00"]
    docs = [
        db_operations.documents.insert(
            data_generator.documents.document_create(created_date=d)
        )
        for d in dates
    ]
    ids = [doc.id for doc in docs]
    elastic_mock.set_search_result("test", ids)

    response = await test_client.get("/search", params={"q": "test"})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [docs[1].id, docs[2].id, docs[0].id]


async def test_search_results_limited_to_20(
    test_client, db_operations, data_generator, elastic_mock,
):
    """Возвращается не более 20 документов."""
    docs = [
        db_operations.documents.insert(data_generator.documents.document_create())
        for _ in range(21)
    ]
    ids = [doc.id for doc in docs]
    elastic_mock.set_search_result("test", ids)

    response = await test_client.get("/search", params={"q": "test"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 20


async def test_search_returns_matching_documents(
    test_client, db_operations, data_generator, elastic_mock,
):
    """Возвращает 200 и документы, найденные через ES + БД."""
    doc1 = db_operations.documents.insert(
        data_generator.documents.document_create(text="hello world")
    )
    doc2 = db_operations.documents.insert(
        data_generator.documents.document_create(text="other document")
    )
    elastic_mock.set_search_result("hello", [doc1.id])

    response = await test_client.get("/search", params={"q": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == doc1.id
    assert body[0]["text"] == doc1.text
    assert body[0]["rubrics"] == doc1.rubrics
    assert body[0]["created_date"] is not None

    assert elastic_mock.search_calls == [{"query": "hello"}]
