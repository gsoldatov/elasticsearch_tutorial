import pytest

from src.config import Config
from src.elastic import ElasticService


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_base_to_head_creates_index(
    test_config: Config,
):
    """upgrade с base на head создаёт все индексы."""
    from src.elastic import ElasticService

    assert len(test_config.es_indices) == 2, (
        "Добавлен новый ES-индекс — обнови этот тест."
    )

    cfg = Config(**{
        **test_config.model_dump(),
        **{
            field: f"{value}_mig_upgrade"
            for field, value in test_config.es_indices.items()
        },
    })
    es = ElasticService(cfg)
    try:
        await es.migrations.upgrade(current="base", to="head")

        for index_name in cfg.es_indices.values():
            assert await es.client.indices.exists(index=index_name), (
                f"Индекс {index_name} не был создан"
            )
    finally:
        await es.migrations.delete_indices()
        await es.close()


async def test_upgrade_same_revision_noop(
    test_config: Config,
):
    """upgrade с одинаковыми current и to — no-op."""
    es = ElasticService(test_config)
    try:
        # Не должно падать, даже если индекс не существует
        await es.migrations.upgrade(current="base", to="base")
        await es.migrations.upgrade(current="head", to="head")
        await es.migrations.upgrade(current="1", to="1")
    finally:
        await es.close()


async def test_upgrade_invalid_revision_raises(
    test_config: Config,
):
    """Невалидная ревизия вызывает ValueError."""
    es = ElasticService(test_config)
    try:
        with pytest.raises(ValueError, match="Неизвестная ревизия"):
            await es.migrations.upgrade(current="foo", to="head")

        with pytest.raises(ValueError, match="вне диапазона"):
            await es.migrations.upgrade(current="base", to="5")
    finally:
        await es.close()
