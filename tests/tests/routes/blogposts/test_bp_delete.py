"""Тесты для DELETE /blogposts/{id}."""

from elasticsearch import ConnectionError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_delete_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_delete = ConnectionError("cluster down")

    response = await test_client_no_db.delete("/blogposts/some-id")

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_delete_nonexistent_returns_204(test_client_no_db):
    """Удаление несуществующего блогпоста — 204 (идемпотентно)."""
    response = await test_client_no_db.delete("/blogposts/nonexistent")

    assert response.status_code == 204
    assert response.content == b""


# ── корректные ─────────────────────────────────────────────────────────────


async def test_delete_existing_blogpost(test_client_no_db, elastic_service_mock):
    """Успешное удаление существующего блогпоста — 204."""
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "T",
        "text": "X",
        "tags": [],
    })

    response = await test_client_no_db.delete("/blogposts/bp-1")

    assert response.status_code == 204
    assert response.content == b""

    assert elastic_service_mock.blogposts.delete_calls == [{"blogpost_id": "bp-1"}]
