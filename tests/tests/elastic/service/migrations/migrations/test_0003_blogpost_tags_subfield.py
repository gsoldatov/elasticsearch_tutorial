import pytest
from elasticsearch import BadRequestError

from src.config import Config
from src.elastic import ElasticService


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_adds_tags_text_subfield(
    test_config: Config,
):
    """Миграция создаёт _v2 с сабфилдом tags._text, данные переносятся."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_up",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        # Применяем миграцию 2, чтобы получить _v1 с данными
        await es.migrations.upgrade(current="1", to="2")

        alias = cfg.es_blogposts_index_name
        v1 = f"{alias}_v1"
        v2 = f"{alias}_v2"

        # Кладём данные в _v1 через alias
        await es.client.index(
            index=alias,
            body={
                "title": "Test",
                "text": "Text",
                "tags": ["python", "fastapi"],
            },
            refresh=True,
        )

        assert await es.client.indices.exists(index=v1)
        assert not await es.client.indices.exists(index=v2)

        # Применяем миграцию 3
        await es.migrations.upgrade(current="2", to="3")

        # _v1 удалён, _v2 существует
        assert not await es.client.indices.exists(index=v1)
        assert await es.client.indices.exists(index=v2)

        # Alias указывает на _v2
        alias_info = await es.client.indices.get(index=alias)
        assert v2 in alias_info

        # Сабфилд tags._as_you_type присутствует в маппинге
        mapping_resp = await es.client.indices.get_mapping(index=alias)
        # get_mapping возвращает ключ реального индекса, не алиаса
        mapping = next(iter(mapping_resp.body.values()))
        tags_props = mapping["mappings"]["properties"]["tags"]
        assert "fields" in tags_props
        assert "_as_you_type" in tags_props["fields"]
        assert tags_props["fields"]["_as_you_type"]["type"] == "search_as_you_type"

        # Данные сохранились после reindex (достаём все документы)
        search_result = await es.client.search(
            index=alias,
            body={"query": {"match_all": {}}},
        )
        hits = search_result["hits"]["hits"]
        assert len(hits) == 1
        assert hits[0]["_source"]["tags"] == ["python", "fastapi"]

    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_already_done_raises(
    test_config: Config,
):
    """Повторный upgrade 2→3 падает — _v2 уже существует."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_up2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="1", to="3")

        with pytest.raises(BadRequestError):
            await es.migrations.upgrade(current="2", to="3")
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_removes_subfield(
    test_config: Config,
):
    """downgrade 3→2 удаляет _v2 и восстанавливает _v1 без сабфилда."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_down",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="1", to="3")

        alias = cfg.es_blogposts_index_name
        v1 = f"{alias}_v1"
        v2 = f"{alias}_v2"

        # Кладём данные через alias (попадают в _v2)
        await es.client.index(
            index=alias,
            body={
                "title": "Test",
                "text": "Text",
                "tags": ["python"],
            },
            refresh=True,
        )

        await es.migrations.downgrade(current="3", to="2")

        # _v2 удалён, _v1 существует
        assert not await es.client.indices.exists(index=v2)
        assert await es.client.indices.exists(index=v1)

        # Alias указывает на _v1
        alias_info = await es.client.indices.get(index=alias)
        assert v1 in alias_info

        # Сабфилда нет в маппинге _v1
        mapping_resp = await es.client.indices.get_mapping(index=alias)
        mapping = next(iter(mapping_resp.body.values()))
        tags_props = mapping["mappings"]["properties"]["tags"]
        assert "fields" not in tags_props

        # Данные сохранились
        search_result = await es.client.search(
            index=alias,
            body={"query": {"match_all": {}}},
        )
        hits = search_result["hits"]["hits"]
        assert len(hits) == 1
        assert hits[0]["_source"]["tags"] == ["python"]
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_idempotent(
    test_config: Config,
):
    """Повторный downgrade не падает."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_down2",
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="1", to="3")
        await es.migrations.downgrade(current="3", to="2")
        # Повторный вызов не должен падать
        await es.migrations.downgrade(current="3", to="2")
    finally:
        await es.migrations.delete_indices()
        await es.close()


# ── guard ──────────────────────────────────────────────────────────────────


async def test_upgrade_without_pipeline_raises(
    test_config: Config,
):
    """upgrade 2→3 без pipeline падает — 0002 не была применена."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_nopipe",
    })
    es = ElasticService(cfg)
    try:
        # Применяем 0002, затем удаляем pipeline
        await es.migrations.upgrade(current="1", to="2")
        pipeline_name = f"{cfg.es_blogposts_index_name}_pipeline"
        v1 = f"{cfg.es_blogposts_index_name}_v1"

        # Снимаем default_pipeline с индекса (иначе ES не даст удалить pipeline)
        await es.client.indices.put_settings(
            index=v1,
            body={"index": {"default_pipeline": None}},
        )
        await es.client.ingest.delete_pipeline(id=pipeline_name)

        with pytest.raises(ValueError, match="не была применена"):
            await es.migrations.upgrade(current="2", to="3")
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_creates_pipeline_if_missing(
    test_config: Config,
):
    """downgrade 3→2 пересоздаёт pipeline, если тот отсутствует."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0003_repipe",
    })
    es = ElasticService(cfg, refresh=True)
    try:
        await es.migrations.upgrade(current="1", to="3")

        # Кладём данные
        alias = cfg.es_blogposts_index_name
        v2 = f"{alias}_v2"
        await es.client.index(
            index=alias,
            body={"title": "T", "text": "X", "tags": ["a"]},
            refresh=True,
        )

        # Снимаем default_pipeline с _v2 и удаляем pipeline
        await es.client.indices.put_settings(
            index=v2,
            body={"index": {"default_pipeline": None}},
        )
        pipeline_name = f"{alias}_pipeline"
        await es.client.ingest.delete_pipeline(id=pipeline_name)

        # downgrade должен пересоздать pipeline и пройти успешно
        await es.migrations.downgrade(current="3", to="2")

        # Pipeline восстановлен
        await es.client.ingest.get_pipeline(id=pipeline_name)

        # Данные сохранились
        search_result = await es.client.search(
            index=alias,
            body={"query": {"match_all": {}}},
        )
        assert len(search_result["hits"]["hits"]) == 1
    finally:
        await es.migrations.delete_indices()
        await es.close()
