"""Тесты для POST /blogposts."""

from elasticsearch import ConnectionError

from src.exceptions import EmbeddingsNetworkError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_create_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_create = ConnectionError("cluster down")

    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["a"]},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_create_ollama_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка Ollama при создании блогпоста — 503."""
    elastic_service_mock.blogposts.raise_on_create = EmbeddingsNetworkError(
        "ollama down"
    )

    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["a"]},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_create_with_custom_id(test_client_no_db, elastic_service_mock):
    """Создание с явно указанным id."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": [], "id": "my-id"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "my-id"
    assert body["title"] == "T"
    assert body["text"] == "X"
    assert body["tags"] == []
    assert body["updated_at"] is not None


async def test_create_duplicate_id_returns_409(
    test_client_no_db, elastic_service_mock,
):
    """Повторное создание с тем же id — 409."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "First", "text": "X", "tags": [], "id": "dup-id"},
    )
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "Second", "text": "Y", "tags": [], "id": "dup-id"},
    )

    assert response.status_code == 409
    assert "уже существует" in response.json()["detail"]


async def test_create_empty_text_allowed(test_client_no_db, elastic_service_mock):
    """Пустой текст разрешён."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "", "tags": []},
    )

    assert response.status_code == 201
    assert response.json()["text"] == ""


async def test_create_empty_tags_allowed(test_client_no_db, elastic_service_mock):
    """Пустые теги разрешены."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    assert response.status_code == 201
    assert response.json()["tags"] == []


async def test_create_without_id_gets_auto_id(test_client_no_db, elastic_service_mock):
    """Без id — ES генерирует авто-id."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["id"].startswith("mock-")


# ── валидация ──────────────────────────────────────────────────────────────


async def test_create_missing_title_returns_422(test_client_no_db):
    """Отсутствует title — 422."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"text": "X", "tags": []},
    )

    assert response.status_code == 422


async def test_create_missing_text_returns_422(test_client_no_db):
    """Отсутствует text — 422."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "tags": []},
    )

    assert response.status_code == 422


async def test_create_missing_tags_returns_422(test_client_no_db):
    """Отсутствует tags — 422."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X"},
    )

    assert response.status_code == 422


async def test_create_empty_title_returns_422(test_client_no_db):
    """Пустой title — 422."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "", "text": "X", "tags": []},
    )

    assert response.status_code == 422


# ── корректные ─────────────────────────────────────────────────────────────


async def test_create_blogpost(test_client_no_db, elastic_service_mock):
    """Успешное создание блогпоста — 201."""
    response = await test_client_no_db.post(
        "/blogposts/",
        json={"title": "Заголовок", "text": "Текст", "tags": ["python"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Заголовок"
    assert body["text"] == "Текст"
    assert body["tags"] == ["python"]
    assert body["updated_at"] is not None

    assert len(elastic_service_mock.blogposts.create_calls) == 1
