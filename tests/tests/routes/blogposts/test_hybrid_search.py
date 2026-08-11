"""Тесты для GET /blogposts/hybrid_search."""

from elasticsearch import ConnectionError


# ── ошибки валидации ───────────────────────────────────────────────────────


async def test_hybrid_search_missing_q_returns_422(test_client_no_db):
    """Отсутствует параметр q — 422."""
    response = await test_client_no_db.get("/blogposts/hybrid_search")
    assert response.status_code == 422


async def test_hybrid_search_empty_q_returns_422(test_client_no_db):
    """Параметр q пустой — 422 (min_length=1)."""
    response = await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": ""},
    )
    assert response.status_code == 422


async def test_hybrid_search_q_too_long_returns_422(test_client_no_db):
    """Параметр q длиннее 256 символов — 422."""
    response = await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": "a" * 257},
    )
    assert response.status_code == 422


# ── ошибки ES ──────────────────────────────────────────────────────────────


async def test_hybrid_search_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES (или Ollama) — 503."""
    elastic_service_mock.blogposts.raise_on_hybrid_search = ConnectionError(
        "cluster down"
    )

    response = await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": "test"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── успешные запросы ───────────────────────────────────────────────────────


async def test_hybrid_search_returns_list(
    test_client_no_db, elastic_service_mock, data_generator,
):
    """Успешный гибридный поиск возвращает список блогпостов."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "Заголовок", "text": "Текст", "tags": ["python"]},
    )

    response = await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": "поисковый запрос"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["title"] == "Заголовок"


async def test_hybrid_search_empty_results_returns_200_empty_list(
    test_client_no_db, elastic_service_mock,
):
    """Пустой результат — 200 с пустым списком."""
    elastic_service_mock.blogposts.set_hybrid_search_result([])

    response = await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": "ничего"},
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_hybrid_search_passes_q_to_service(
    test_client_no_db, elastic_service_mock,
):
    """Параметр q передаётся в сервис."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    await test_client_no_db.get(
        "/blogposts/hybrid_search", params={"q": "мой запрос"},
    )

    last_call = elastic_service_mock.blogposts.hybrid_search_calls[-1]
    assert last_call["query"] == "мой запрос"
    assert last_call["size"] == 20  # default
