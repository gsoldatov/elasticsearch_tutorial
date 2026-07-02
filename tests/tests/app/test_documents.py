from unittest.mock import patch

from sqlalchemy.exc import OperationalError


async def test_delete_db_operational_error_returns_503(test_client):
    """Ошибка соединения с БД — 503."""
    with patch(
        "src.db.repository.document.DocumentRepository.delete_by_id",
        side_effect=OperationalError("connection refused", None, None),
    ):
        response = await test_client.delete("/documents/1")

    assert response.status_code == 503
    assert response.json()["detail"] == "Service unavailable"


async def test_delete_nonexistent_document_returns_404(test_client):
    """Документ не существует — 404."""
    response = await test_client.delete("/documents/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


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
