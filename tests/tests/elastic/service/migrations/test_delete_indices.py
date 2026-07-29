from src.config import Config
from src.elastic import ElasticService


# ── delete_indices ─────────────────────────────────────────────────────────


async def test_delete_indices_removes_index(
    test_config: Config,
):
    """delete_indices удаляет все индексы."""
    assert len(test_config.es_indices) == 1, (
        "Добавлен новый ES-индекс — обнови этот тест."
    )

    saved = test_config.es_documents_index_name
    test_config.es_documents_index_name = f"{saved}_mig_delidx"
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()

        for index_name in test_config.es_indices.values():
            assert not await es.client.indices.exists(index=index_name), (
                f"Индекс {index_name} не был удалён"
            )
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved


async def test_delete_indices_idempotent(
    test_config: Config,
):
    """Повторный вызов delete_indices не падает."""
    assert len(test_config.es_indices) == 1, (
        "Добавлен новый ES-индекс — обнови этот тест."
    )

    saved = test_config.es_documents_index_name
    test_config.es_documents_index_name = f"{saved}_mig_delidx2"
    es = ElasticService(test_config)
    try:
        await es.migrations.upgrade(current="base", to="head")
        await es.migrations.delete_indices()
        # Повторный вызов не должен падать
        await es.migrations.delete_indices()
    finally:
        await es.migrations.delete_indices()
        await es.close()
        test_config.es_documents_index_name = saved
