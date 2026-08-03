import pytest
from elasticsearch import NotFoundError

from src.config import Config
from src.elastic import ElasticService


# ── delete_indices ─────────────────────────────────────────────────────────


async def test_delete_indices_removes_index(
    test_config: Config,
):
    """delete_indices удаляет все индексы (включая версионированные)."""
    assert len(test_config.es_indices) == 3, (
        "Добавлен новый ES-индекс — обнови этот тест."
    )
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_delidx"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()

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


async def test_delete_indices_removes_pipelines(
    test_config: Config,
):
    """delete_indices удаляет все ingest pipelines."""
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_delpipe"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()

        assert len(es.migrations._revisions) == 4, (
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


async def test_delete_indices_removes_aliases(
    test_config: Config,
):
    """delete_indices удаляет все aliases."""
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_delalias"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()

        assert len(es.migrations._revisions) == 4, (
            "Добавлена новая миграция — обнови этот тест: "
            "проверь, что список ожидаемых aliases актуален."
        )

        aliases = [
            cfg.es_blogposts_index_name,
            cfg.es_sales_index_name,
        ]
        for alias in aliases:
            assert not await es.client.indices.exists_alias(name=alias), (
                f"Остался alias: {alias}"
            )
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_delete_indices_idempotent(
    test_config: Config,
):
    """Повторный вызов delete_indices не падает."""
    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_delidx2"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()
        # Повторный вызов не должен падать
        await es.migrations.delete_indices()
    finally:
        await es.migrations.delete_indices()
        await es.close()
