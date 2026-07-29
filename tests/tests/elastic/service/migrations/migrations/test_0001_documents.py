import pytest
from elasticsearch import BadRequestError

from src.config import Config
from src.elastic import ElasticService


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_creates_index_with_correct_settings(
    test_config: Config,
):
    """Миграция создаёт индекс с корректными настройками и маппингом."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_0001_up"
    es = ElasticService(test_config, refresh=True)
    try:
        await es.migrations.upgrade(current="base", to="1")

        # Проверяем, что индекс существует и принимает документы
        await es.documents.index_documents([
            {"id": 1, "text": "тестовый документ"},
        ])
        result = await es.documents.search("тестовый")
        assert result == [1]
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved


async def test_upgrade_index_already_exists_raises(
    test_config: Config,
):
    """Повторный upgrade падает — индекс уже существует."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_0001_up2"
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="1")

        with pytest.raises(BadRequestError):
            await es.migrations.upgrade(current="base", to="1")
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_deletes_index(
    test_config: Config,
):
    """downgrade удаляет индекс."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_0001_down"
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="1")
        await es.migrations.downgrade(current="1", to="base")

        exists = await es.client.indices.exists(index=idx)
        assert not exists
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved


async def test_downgrade_idempotent(
    test_config: Config,
):
    """Повторный downgrade не падает — индекс уже удалён."""
    saved = test_config.es_documents_index_name
    idx = test_config.es_documents_index_name = f"{saved}_0001_down2"
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="1")
        await es.migrations.downgrade(current="1", to="base")
        # Повторный вызов не должен падать
        await es.migrations.downgrade(current="1", to="base")
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved
