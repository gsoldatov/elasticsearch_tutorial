import pytest
from elasticsearch import BadRequestError, NotFoundError

from src.config import Config
from src.elastic import ElasticService


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_creates_index_and_pipeline(
    test_config: Config,
):
    """Миграция создаёт индекс, alias, pipeline — alias принимает документы."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0002_up",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="1", to="2")

        alias = cfg.es_blogposts_index_name
        real_index = f"{alias}_v1"

        # v1-индекс существует
        assert await es.client.indices.exists(index=real_index)
        # Alias существует
        assert await es.client.indices.exists(index=alias)
        # Pipeline существует
        pipeline_name = f"{alias}_pipeline"
        pipelines = await es.client.ingest.get_pipeline(id=pipeline_name)
        assert pipeline_name in pipelines

        # Индексация документа через alias (ID генерируется ES)
        resp = await es.client.index(
            index=alias,
            body={
                "title": "Test Title",
                "text": "Test text",
                "tags": ["test"],
            },
            refresh=True,
        )
        doc_id = resp["_id"]
        doc = await es.client.get(index=alias, id=doc_id)
        source = doc["_source"]
        assert source["title"] == "Test Title"
        assert source["text"] == "Test text"
        assert source["tags"] == ["test"]
        assert "updated_at" in source
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_already_exists_raises(
    test_config: Config,
):
    """Повторный upgrade падает — индекс уже существует."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0002_up2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="1", to="2")

        with pytest.raises(BadRequestError):
            await es.migrations.upgrade(current="1", to="2")
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_pipeline_does_not_override_updated_at(
    test_config: Config,
):
    """Pipeline не перезаписывает updated_at при обновлении документа."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0002_pipe",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="1", to="2")

        alias = cfg.es_blogposts_index_name

        # Создаём документ (updated_at ставится pipeline)
        resp = await es.client.index(
            index=alias,
            body={
                "title": "Original",
                "text": "Text",
                "tags": ["a"],
            },
            refresh=True,
        )
        doc_id = resp["_id"]
        doc = await es.client.get(index=alias, id=doc_id)
        first_updated_at = doc["_source"]["updated_at"]

        # Обновляем документ с новым updated_at
        new_ts = "2025-06-15T12:00:00Z"
        await es.client.index(
            index=alias,
            id=doc_id,
            body={
                "title": "Updated",
                "text": "Text",
                "tags": ["a"],
                "updated_at": new_ts,
            },
            refresh=True,
        )
        doc = await es.client.get(index=alias, id=doc_id)
        assert doc["_source"]["updated_at"] == new_ts
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_deletes_index_and_pipeline(
    test_config: Config,
):
    """downgrade удаляет индекс, alias и pipeline."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0002_down",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="1", to="2")
        await es.migrations.downgrade(current="2", to="1")

        alias = cfg.es_blogposts_index_name
        real_index = f"{alias}_v1"

        # v1-индекс удалён
        assert not await es.client.indices.exists(index=real_index)
        # Alias удалён
        assert not await es.client.indices.exists(index=alias)

        pipeline_name = f"{alias}_pipeline"
        with pytest.raises(NotFoundError):
            await es.client.ingest.get_pipeline(id=pipeline_name)
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_idempotent(
    test_config: Config,
):
    """Повторный downgrade не падает — всё уже удалено."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0002_down2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="1", to="2")
        await es.migrations.downgrade(current="2", to="1")
        # Повторный вызов не должен падать
        await es.migrations.downgrade(current="2", to="1")
    finally:
        await es.migrations.delete_indices()
        await es.close()
