import pytest
from elasticsearch import BadRequestError, NotFoundError

from src.config import Config
from src.elastic import ElasticService


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_creates_index_and_alias(
    test_config: Config,
):
    """Миграция создаёт индекс, alias — alias принимает документы."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_sales_index_name": f"{test_config.es_sales_index_name}_0004_up",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="3", to="4")

        alias = cfg.es_sales_index_name
        real_index = f"{alias}_v1"

        # v1-индекс существует
        assert await es.client.indices.exists(index=real_index)
        # Alias существует
        assert await es.client.indices.exists(index=alias)

        # Индексация документа через alias (ID генерируется ES)
        resp = await es.client.index(
            index=alias,
            body={
                "date": "2025-06-15T12:00:00Z",
                "region": "Россия",
                "product": "тестовый продукт",
                "units_sold": 10,
                "price": 1500.00,
                "revenue": 15000.00,
            },
            refresh=True,
        )
        doc_id = resp["_id"]
        doc = await es.client.get(index=alias, id=doc_id)
        source = doc["_source"]
        assert source["region"] == "Россия"
        assert source["product"] == "тестовый продукт"
        assert source["units_sold"] == 10
        assert source["price"] == 1500.0
        assert source["revenue"] == 15000.0
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_already_exists_raises(
    test_config: Config,
):
    """Повторный upgrade падает — индекс уже существует."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_sales_index_name": f"{test_config.es_sales_index_name}_0004_up2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="3", to="4")

        with pytest.raises(BadRequestError):
            await es.migrations.upgrade(current="3", to="4")
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_deletes_index_and_alias(
    test_config: Config,
):
    """downgrade удаляет индекс и alias."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_sales_index_name": f"{test_config.es_sales_index_name}_0004_down",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="3", to="4")
        await es.migrations.downgrade(current="4", to="3")

        alias = cfg.es_sales_index_name
        real_index = f"{alias}_v1"

        # v1-индекс удалён
        assert not await es.client.indices.exists(index=real_index)
        # Alias удалён
        assert not await es.client.indices.exists(index=alias)
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_idempotent(
    test_config: Config,
):
    """Повторный downgrade не падает — всё уже удалено."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_sales_index_name": f"{test_config.es_sales_index_name}_0004_down2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="3", to="4")
        await es.migrations.downgrade(current="4", to="3")
        # Повторный вызов не должен падать
        await es.migrations.downgrade(current="4", to="3")
    finally:
        await es.migrations.delete_indices()
        await es.close()
