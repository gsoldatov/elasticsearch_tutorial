"""Тесты для GET /blogposts/{id}."""

from elasticsearch import ConnectionError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_get_nonexistent_returns_404(test_client_no_db, elastic_service_mock):
    """Блогпост не найден — 404."""
    response = await test_client_no_db.get("/blogposts/nonexistent")

    assert response.status_code == 404
    assert "не найден" in response.json()["detail"].lower()


async def test_get_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_get = ConnectionError("cluster down")

    response = await test_client_no_db.get("/blogposts/some-id")

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── корректные ─────────────────────────────────────────────────────────────


async def test_get_existing_blogpost(test_client_no_db, elastic_service_mock):
    """Успешное получение блогпоста."""
    # Создаём через сервис, чтобы был в мок-хранилище
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "Заголовок",
        "text": "Текст",
        "tags": ["python"],
    })

    response = await test_client_no_db.get("/blogposts/bp-1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "bp-1"
    assert body["title"] == "Заголовок"
    assert body["text"] == "Текст"
    assert body["tags"] == ["python"]
    assert body["updated_at"] is not None

    assert elastic_service_mock.blogposts.get_calls == [{"blogpost_id": "bp-1"}]
