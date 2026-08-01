from datetime import datetime, timezone

import pytest
from elasticsearch import BadRequestError

from src.config import Config
from src.elastic import ElasticService
from src.models.document import Document


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_creates_index_with_correct_settings(
    test_config: Config,
):
    """Миграция создаёт индекс с корректными настройками и маппингом."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": f"{test_config.es_documents_index_name}_0001_up",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="base", to="1")

        # Проверяем, что индекс существует и принимает документы
        await es.documents.index_documents([
            Document(id=1, text="тестовый документ", rubrics=[], created_date=datetime.now(timezone.utc)),
        ])
        result = await es.documents.search("тестовый")
        assert result == [1]
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_index_already_exists_raises(
    test_config: Config,
):
    """Повторный upgrade падает — индекс уже существует."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": f"{test_config.es_documents_index_name}_0001_up2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="1")

        with pytest.raises(BadRequestError):
            await es.migrations.upgrade(current="base", to="1")
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_deletes_index(
    test_config: Config,
):
    """downgrade удаляет индекс."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": f"{test_config.es_documents_index_name}_0001_down",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="1")
        await es.migrations.downgrade(current="1", to="base")

        exists = await es.client.indices.exists(index=cfg.es_documents_index_name)
        assert not exists
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_idempotent(
    test_config: Config,
):
    """Повторный downgrade не падает — индекс уже удалён."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_documents_index_name": f"{test_config.es_documents_index_name}_0001_down2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="1")
        await es.migrations.downgrade(current="1", to="base")
        # Повторный вызов не должен падать
        await es.migrations.downgrade(current="1", to="base")
    finally:
        await es.migrations.delete_indices()
        await es.close()
