"""Тесты для PATCH /blogposts/{id}."""

from datetime import datetime, timezone

from elasticsearch import ConnectionError

from src.exceptions import UpdateConflict


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_update_missing_blogpost_returns_404(
    test_client_no_db, elastic_service_mock,
):
    """Блогпост не найден — 404."""
    response = await test_client_no_db.patch(
        "/blogposts/nonexistent",
        json={"title": "New"},
    )

    assert response.status_code == 404


async def test_update_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_update = ConnectionError("cluster down")

    response = await test_client_no_db.patch(
        "/blogposts/some-id",
        json={"title": "New"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_update_conflict_returns_409(
    test_client_no_db, elastic_service_mock,
):
    """Конфликт optimistic lock — 409."""
    # Создаём блогпост, он должен быть в хранилище
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "Original",
        "text": "Text",
        "tags": [],
    })
    elastic_service_mock.blogposts.raise_on_update = UpdateConflict(
        "Конфликт версий документа. Попробуйте позже."
    )

    response = await test_client_no_db.patch(
        "/blogposts/bp-1",
        json={"title": "New"},
    )

    assert response.status_code == 409
    assert "Конфликт" in response.json()["detail"]


# ── валидация ──────────────────────────────────────────────────────────────


async def test_update_empty_body_returns_422(test_client_no_db):
    """Пустое тело — 422 (AnyOf)."""
    response = await test_client_no_db.patch(
        "/blogposts/bp-1",
        json={},
    )

    assert response.status_code == 422


# ── корректные ─────────────────────────────────────────────────────────────


async def test_update_single_field(test_client_no_db, elastic_service_mock):
    """Частичное обновление одного поля."""
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "Original",
        "text": "Text",
        "tags": ["old"],
    })

    response = await test_client_no_db.patch(
        "/blogposts/bp-1",
        json={"title": "Updated Title"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "bp-1"
    assert body["title"] == "Updated Title"
    assert body["text"] == "Text"
    assert body["tags"] == ["old"]


async def test_update_multiple_fields(test_client_no_db, elastic_service_mock):
    """Частичное обновление нескольких полей."""
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "Original",
        "text": "Text",
        "tags": ["old"],
    })

    response = await test_client_no_db.patch(
        "/blogposts/bp-1",
        json={"title": "New", "tags": ["new"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New"
    assert body["tags"] == ["new"]


async def test_update_with_provided_updated_at(
    test_client_no_db, elastic_service_mock,
):
    """PATCH принимает updated_at в теле запроса."""
    await elastic_service_mock.blogposts.create({
        "id": "bp-1",
        "title": "Original",
        "text": "Text",
        "tags": [],
    })

    response = await test_client_no_db.patch(
        "/blogposts/bp-1",
        json={"title": "New", "updated_at": "2025-06-15T12:00:00Z"},
    )

    assert response.status_code == 200
    assert elastic_service_mock.blogposts.update_calls[-1] == {
        "blogpost_id": "bp-1",
        "data": {
            "title": "New",
            "updated_at": datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        },
    }
