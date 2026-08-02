import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_head_to_base_deletes_index(
    test_config: Config,
):
    """downgrade с head на base удаляет все индексы (включая версионированные)."""
    assert len(test_config.es_indices) == 2, (
        "Добавлен новый ES-индекс — обнови этот тест."
    )
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_downgrade"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.downgrade(current="head", to="base")

        for name, index_name in cfg.es_indices.items():
            resp = await es.client.cat.indices(
                index=f"{index_name}*",
                format="json",
            )
            assert resp == [], (
                f"Остались индексы, соответствующие шаблону "
                f"{index_name}* ({name}): {resp}"
            )
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_head_to_base_deletes_pipelines(
    test_config: Config,
):
    """downgrade с head на base удаляет все ingest pipelines."""
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_downpipe"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.downgrade(current="head", to="base")

        assert len(es.migrations._revisions) == 3, (
            "Добавлена новая миграция — обнови этот тест: "
            "проверь, что список ожидаемых pipelines актуален."
        )

        pipelines = [
            f"{cfg.es_blogposts_index_name}_pipeline",
        ]
        for pipeline_name in pipelines:
            with pytest.raises(NotFoundError):
                await es.client.ingest.get_pipeline(id=pipeline_name)
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_head_to_base_deletes_aliases(
    test_config: Config,
):
    """downgrade с head на base удаляет все aliases."""
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_downalias"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.downgrade(current="head", to="base")

        assert len(es.migrations._revisions) == 3, (
            "Добавлена новая миграция — обнови этот тест: "
            "проверь, что список ожидаемых aliases актуален."
        )

        aliases = [
            cfg.es_blogposts_index_name,
        ]
        for alias in aliases:
            assert not await es.client.indices.exists_alias(name=alias), (
                f"Остался alias: {alias}"
            )
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_downgrade_same_revision_noop(
    test_config: Config,
):
    """downgrade с одинаковыми current и to — no-op."""
    es = ElasticService(test_config)
    try:
        await es.migrations.downgrade(current="base", to="base")
        await es.migrations.downgrade(current="head", to="head")
        await es.migrations.downgrade(current="1", to="1")
    finally:
        await es.close()


async def test_downgrade_invalid_revision_raises(
    test_config: Config,
):
    """Невалидная ревизия вызывает ValueError."""
    es = ElasticService(test_config)
    try:
        with pytest.raises(ValueError, match="Неизвестная ревизия"):
            await es.migrations.downgrade(current="abc", to="base")

        with pytest.raises(ValueError, match="вне диапазона"):
            await es.migrations.downgrade(current="5", to="base")
    finally:
        await es.close()
