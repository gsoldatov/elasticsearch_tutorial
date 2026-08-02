"""Тесты для GET /blogposts/search_tags."""

from elasticsearch import ConnectionError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_search_tags_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_search_tags = (
        ConnectionError("cluster down")
    )

    response = await test_client_no_db.get("/blogposts/search_tags", params={"q": "py"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_search_tags_missing_q_returns_422(test_client_no_db):
    """Отсутствует параметр q — 422."""
    response = await test_client_no_db.get("/blogposts/search_tags")
    assert response.status_code == 422


async def test_search_tags_empty_q_returns_422(test_client_no_db):
    """Параметр q пустой — 422 (min_length=1)."""
    response = await test_client_no_db.get(
        "/blogposts/search_tags", params={"q": ""},
    )
    assert response.status_code == 422


async def test_search_tags_q_too_long_returns_422(test_client_no_db):
    """Параметр q длиннее 256 символов — 422."""
    response = await test_client_no_db.get(
        "/blogposts/search_tags", params={"q": "a" * 257},
    )
    assert response.status_code == 422


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_search_tags_no_matches_returns_404(
    test_client_no_db, elastic_service_mock,
):
    """Нет совпадений — 404."""
    response = await test_client_no_db.get(
        "/blogposts/search_tags", params={"q": "zzz"},
    )
    assert response.status_code == 404
    assert "не найдены" in response.json()["detail"]


# ── корректные ─────────────────────────────────────────────────────────────


async def test_search_tags_returns_sorted_list(
    test_client_no_db, elastic_service_mock,
):
    """Успешный запрос возвращает список тегов."""
    # Создаём блогпост с тегами
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["python", "fastapi"]},
    )
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["pytest", "python"]},
    )

    response = await test_client_no_db.get(
        "/blogposts/search_tags", params={"q": "py"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == ["pytest", "python"]


async def test_search_tags_q_passed_to_service(
    test_client_no_db, elastic_service_mock,
):
    """Параметр q передаётся в сервис."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["python"]},
    )

    await test_client_no_db.get(
        "/blogposts/search_tags", params={"q": "py"},
    )

    last_call = elastic_service_mock.blogposts.search_tags_calls[-1]
    assert last_call["q"] == "py"
