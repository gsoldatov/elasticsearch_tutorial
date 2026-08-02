"""Тесты для GET /blogposts/search."""

from elasticsearch import ConnectionError


# ── ошибки ─────────────────────────────────────────────────────────────────


async def test_search_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.blogposts.raise_on_search = ConnectionError("cluster down")

    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "test"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


async def test_search_missing_q_returns_422(test_client_no_db):
    """Отсутствует параметр q — 422."""
    response = await test_client_no_db.get("/blogposts/search")
    assert response.status_code == 422


async def test_search_empty_q_returns_422(test_client_no_db):
    """Параметр q пустой — 422 (min_length=1)."""
    response = await test_client_no_db.get("/blogposts/search", params={"q": ""})
    assert response.status_code == 422


async def test_search_q_too_long_returns_422(test_client_no_db):
    """Параметр q длиннее 256 символов — 422."""
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "a" * 257},
    )
    assert response.status_code == 422


async def test_search_tags_too_many_returns_422(test_client_no_db):
    """Более 10 тегов — 422."""
    response = await test_client_no_db.get(
        "/blogposts/search",
        params={"q": "test", "tags": ",".join(str(i) for i in range(11))},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "tags"]
    assert "не более 10 элементов" in detail[0]["msg"]


async def test_search_tag_too_long_returns_422(test_client_no_db):
    """Тег длиннее 64 символов — 422."""
    response = await test_client_no_db.get(
        "/blogposts/search",
        params={"q": "test", "tags": "python," + "x" * 65},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "tags"]


async def test_search_tag_too_short_returns_422(test_client_no_db):
    """Пустой тег — 422."""
    response = await test_client_no_db.get(
        "/blogposts/search",
        params={"q": "test", "tags": "python,,"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "tags"]


async def test_search_p_zero_returns_422(test_client_no_db):
    """p=0 — 422 (ge=1)."""
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "test", "p": "0"},
    )
    assert response.status_code == 422


async def test_search_p_over_1_mln_returns_422(test_client_no_db):
    """p=0 — 422 (ge=1)."""
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "test", "p": "1000001"},
    )
    assert response.status_code == 422


async def test_search_per_page_zero_returns_422(test_client_no_db):
    """per_page=0 — 422 (ge=1)."""
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "test", "per_page": "0"},
    )
    assert response.status_code == 422


async def test_search_per_page_over_100_returns_422(test_client_no_db):
    """per_page=101 — 422 (le=100)."""
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "test", "per_page": "101"},
    )
    assert response.status_code == 422


# ── граничные случаи ───────────────────────────────────────────────────────


async def test_search_no_matches_returns_404(test_client_no_db, elastic_service_mock):
    """Нет совпадений — 404."""
    # Мок без блогпостов — search вернёт NotFoundException
    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "nothing"},
    )
    assert response.status_code == 404
    assert "не найдены" in response.json()["detail"]


# ── корректные ─────────────────────────────────────────────────────────────


async def test_search_returns_items_and_total(
    test_client_no_db, elastic_service_mock, data_generator,
):
    """Успешный поиск возвращает items и total."""
    # Создаём блогпост через мок, чтобы search вернул результат
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "Заголовок", "text": "Текст", "tags": ["python"]},
    )

    response = await test_client_no_db.get(
        "/blogposts/search", params={"q": "Заголовок"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Заголовок"


async def test_search_pagination_passed_to_service(
    test_client_no_db, elastic_service_mock,
):
    """Параметры p и per_page передаются в сервис."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    await test_client_no_db.get(
        "/blogposts/search",
        params={"q": "T", "p": "3", "per_page": "10"},
    )

    last_call = elastic_service_mock.blogposts.search_calls[-1]
    assert last_call["page"] == 3
    assert last_call["per_page"] == 10


async def test_search_tags_parsed_and_passed(
    test_client_no_db, elastic_service_mock,
):
    """Теги парсятся из строки и передаются списком в сервис."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": ["python"]},
    )

    await test_client_no_db.get(
        "/blogposts/search",
        params={"q": "T", "tags": "python,fastapi, django"},
    )

    last_call = elastic_service_mock.blogposts.search_calls[-1]
    assert last_call["tags"] == ["python", "fastapi", "django"]


async def test_search_min_max_time_passed_to_service(
    test_client_no_db, elastic_service_mock,
):
    """min_time и max_time передаются в сервис."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    await test_client_no_db.get(
        "/blogposts/search",
        params={
            "q": "T",
            "min_time": "2025-01-01T00:00:00",
            "max_time": "2025-06-15T00:00:00",
        },
    )

    last_call = elastic_service_mock.blogposts.search_calls[-1]
    assert last_call["min_time"] is not None
    assert last_call["max_time"] is not None


async def test_search_default_pagination_values(
    test_client_no_db, elastic_service_mock,
):
    """Значения пагинации по умолчанию: p=1, per_page=20."""
    await test_client_no_db.post(
        "/blogposts/",
        json={"title": "T", "text": "X", "tags": []},
    )

    await test_client_no_db.get(
        "/blogposts/search", params={"q": "T"},
    )

    last_call = elastic_service_mock.blogposts.search_calls[-1]
    assert last_call["page"] == 1
    assert last_call["per_page"] == 20
