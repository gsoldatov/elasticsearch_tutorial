"""Тесты для GET /sales/by_month_and_region."""

from elasticsearch import ConnectionError


# ── ошибки валидации ───────────────────────────────────────────────────────


async def test_region_too_many_returns_422(test_client_no_db):
    """Более 10 регионов — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"region": ",".join(str(i) for i in range(11))},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "region"]
    assert "не более 10 элементов" in detail[0]["msg"]


async def test_region_too_long_returns_422(test_client_no_db):
    """Регион длиннее 64 символов — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"region": "x" * 65},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "region"]


async def test_products_too_many_returns_422(test_client_no_db):
    """Более 10 продуктов — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"products": ",".join(str(i) for i in range(11))},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "products"]
    assert "не более 10 элементов" in detail[0]["msg"]


async def test_products_too_long_returns_422(test_client_no_db):
    """Продукт длиннее 64 символов — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"products": "x" * 65},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "products"]


async def test_min_date_invalid_returns_422(test_client_no_db):
    """min_date с невалидной датой — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"min_date": "not-a-date"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "min_date"]


async def test_max_date_invalid_returns_422(test_client_no_db):
    """max_date с невалидной датой — 422."""
    response = await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={"max_date": "2025-13-01"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["query", "max_date"]


# ── ошибки соединения ──────────────────────────────────────────────────────


async def test_es_connection_error_returns_503(
    test_client_no_db, elastic_service_mock,
):
    """Ошибка соединения с ES — 503."""
    elastic_service_mock.sales.raise_on_by_month_and_region = ConnectionError("cluster down")

    response = await test_client_no_db.get("/sales/by_month_and_region")

    assert response.status_code == 503
    assert response.json()["detail"] == "Сервис недоступен"


# ── edge cases ─────────────────────────────────────────────────────────────


async def test_empty_result_returns_200_empty_list(
    test_client_no_db, elastic_service_mock,
):
    """Пустой результат — 200 + []."""
    response = await test_client_no_db.get("/sales/by_month_and_region")

    assert response.status_code == 200
    assert response.json() == []


# ── корректные ─────────────────────────────────────────────────────────────


async def test_passes_filters_to_service(
    test_client_no_db, elastic_service_mock,
):
    """Все параметры передаются в сервис."""
    await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={
            "min_date": "2025-01-01",
            "max_date": "2025-12-31",
            "region": "Россия, Германия",
            "products": "ноутбук, телефон",
        },
    )

    last_call = elastic_service_mock.sales.by_month_and_region_calls[-1]
    assert last_call["regions"] == ["Россия", "Германия"]
    assert last_call["products"] == ["ноутбук", "телефон"]
    assert last_call["min_date"].isoformat() == "2025-01-01"
    assert last_call["max_date"].isoformat() == "2025-12-31"


async def test_strips_whitespace_from_csv_params(
    test_client_no_db, elastic_service_mock,
):
    """Пробелы вокруг запятых удаляются при парсинге region и products."""
    await test_client_no_db.get(
        "/sales/by_month_and_region",
        params={
            "region": " Россия ,  Германия ",
            "products": " ноутбук , телефон ",
        },
    )

    last_call = elastic_service_mock.sales.by_month_and_region_calls[-1]
    assert last_call["regions"] == ["Россия", "Германия"]
    assert last_call["products"] == ["ноутбук", "телефон"]


async def test_no_params_returns_all(
    test_client_no_db, elastic_service_mock,
):
    """Без параметров — вызов без фильтров."""
    await test_client_no_db.get("/sales/by_month_and_region")

    last_call = elastic_service_mock.sales.by_month_and_region_calls[-1]
    assert last_call["min_date"] is None
    assert last_call["max_date"] is None
    assert last_call["regions"] is None
    assert last_call["products"] is None
