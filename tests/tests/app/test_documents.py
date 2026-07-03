from unittest.mock import patch

from elasticsearch import ConnectionError
from sqlalchemy.exc import OperationalError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_delete_db_operational_error_returns_503(test_client):
    """Ошибка соединения с БД — 503."""
    with patch(
        "src.db.repository.document.DocumentRepository.delete_by_id",
        side_effect=OperationalError("connection refused", None, None),
    ):
        response = await test_client.delete("/documents/1")

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_delete_es_error_returns_503(
    test_client, elastic_mock,
):
    """Ошибка Elasticsearch при удалении — 503."""
    elastic_mock.raise_on_delete = ConnectionError("cluster down")
    response = await test_client.delete("/documents/1")

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_delete_es_error_does_not_call_db(
    test_client, db_operations, data_generator, elastic_mock,
):
    """При ошибке ES удаление из БД не происходит."""
    doc = db_operations.documents.insert(data_generator.documents.document_create())
    elastic_mock.raise_on_delete = ConnectionError("cluster down")

    response = await test_client.delete(f"/documents/{doc.id}")

    assert response.status_code == 503
    assert db_operations.documents.by_id(doc.id) is not None


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_delete_nonexistent_document_returns_404(test_client):
    """Документ не существует — 404."""
    response = await test_client.delete("/documents/99999")

    assert response.status_code == 404
    assert "не найден" in response.json()["detail"].lower()


# ── корректные ─────────────────────────────────────────────────────────────


async def test_delete_existing_document(
    test_client, db_operations, data_generator, elastic_mock,
):
    """Удаляет существующий документ — 204, документ исчезает из БД."""
    doc = db_operations.documents.insert(data_generator.documents.document_create())

    response = await test_client.delete(f"/documents/{doc.id}")

    assert response.status_code == 204
    assert response.content == b""
    assert db_operations.documents.by_id(doc.id) is None
    assert elastic_mock.delete_calls == [{"doc_id": doc.id}]
