import pytest

from src.config import Config
from src.elastic import ElasticService


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_head_to_base_deletes_index(
    test_config: Config,
):
    """downgrade с head на base удаляет все индексы."""
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

        for index_name in cfg.es_indices.values():
            assert not await es.client.indices.exists(index=index_name), (
                f"Индекс {index_name} не был удалён"
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
