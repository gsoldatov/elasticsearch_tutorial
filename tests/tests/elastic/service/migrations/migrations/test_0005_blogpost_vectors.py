from typing import AsyncGenerator

import pytest
from elasticsearch import BadRequestError

from src.models.blogpost import BlogpostTextChunk
from src.models.config import Config
from src.elastic import ElasticService
from tests.mocks.elastic_mock import BlogpostsEmbeddingsMock


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
async def elastic_with_mocked_embeddings(
    request: pytest.FixtureRequest,
    test_config: Config,
) -> AsyncGenerator[tuple[ElasticService, BlogpostsEmbeddingsMock], None]:
    """ElasticService с замоканными эмбеддингами и авто-очисткой.

    Настраивает уникальные имена индексов по имени теста,
    подменяет blogposts.embeddings на BlogpostsEmbeddingsMock,
    после теста удаляет индексы и закрывает клиент.
    """
    suffix = request.node.name.replace("[", "_").replace("]", "")

    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": (
            f"{test_config.es_blogposts_index_name}_{suffix}"
        ),
        "es_blogposts_text_chunks_index_name": (
            f"{test_config.es_blogposts_text_chunks_index_name}_{suffix}"
        ),
    })
    es = ElasticService(cfg, refresh=True)
    mock = BlogpostsEmbeddingsMock()
    orig = es.blogposts._embeddings
    es.blogposts._embeddings = mock
    try:
        yield es, mock
    finally:
        es.blogposts._embeddings = orig
        await es.migrations.delete_indices()
        await es.close()


# ── upgrade ────────────────────────────────────────────────────────────────


async def test_upgrade_adds_title_vector_and_chunks(
    elastic_with_mocked_embeddings: tuple[
        ElasticService, BlogpostsEmbeddingsMock,
    ],
):
    """Миграция создаёт _v3 с title_vector и индекс чанков, данные переносятся."""
    es, mock = elastic_with_mocked_embeddings
    cfg = es._config

    mock_vector = [0.1] * 384
    mock_chunks = [
        BlogpostTextChunk(
            blogpost_id="bp-1",
            chunk_index=0,
            chunk_text="Тестовый текст блогпоста для проверки миграции векторов.",
            chunk_vector=mock_vector,
        ),
    ]
    mock.set_result("bp-1", title_vector=mock_vector, chunks=mock_chunks)

    # Применяем миграции до 3 (получаем _v2 с данными)
    await es.migrations.upgrade(current="1", to="3")

    alias = cfg.es_blogposts_index_name
    v2 = f"{alias}_v2"
    v3 = f"{alias}_v3"
    chunks_index = cfg.es_blogposts_text_chunks_index_name

    # Кладём данные в _v2 через alias с явным id
    await es.client.index(
        index=alias,
        id="bp-1",
        body={
            "title": "Тестовый заголовок",
            "text": "Тестовый текст блогпоста для проверки миграции векторов.",
            "tags": ["python", "fastapi"],
        },
        refresh=True,
    )

    assert await es.client.indices.exists(index=v2)
    assert not await es.client.indices.exists(index=v3)
    assert not await es.client.indices.exists(index=chunks_index)

    # Применяем миграцию 5 (через 4 — sales, но blogposts уже на 3)
    await es.migrations.upgrade(current="3", to="5")

    # _v2 удалён, _v3 существует
    assert not await es.client.indices.exists(index=v2)
    assert await es.client.indices.exists(index=v3)
    assert await es.client.indices.exists(index=chunks_index)

    # Alias указывает на _v3
    alias_info = await es.client.indices.get(index=alias)
    assert v3 in alias_info

    # title_vector присутствует в маппинге
    mapping_resp = await es.client.indices.get_mapping(index=alias)
    mapping = next(iter(mapping_resp.body.values()))
    props = mapping["mappings"]["properties"]
    assert "title_vector" in props
    tv = props["title_vector"]
    assert tv["type"] == "dense_vector"
    assert tv["dims"] == 384

    # Данные сохранились после миграции
    search_result = await es.client.search(
        index=alias,
        body={"query": {"match_all": {}}},
    )
    hits = search_result["hits"]["hits"]
    assert len(hits) == 1
    doc = hits[0]["_source"]
    assert doc["title"] == "Тестовый заголовок"
    assert doc["text"] == "Тестовый текст блогпоста для проверки миграции векторов."
    assert "title_vector" in doc
    assert len(doc["title_vector"]) == 384

    # Чанки в индексе чанков
    chunks_resp = await es.client.search(
        index=chunks_index,
        body={"query": {"match_all": {}}},
    )
    chunk_hits = chunks_resp["hits"]["hits"]
    assert len(chunk_hits) == 1
    cs = chunk_hits[0]["_source"]
    assert cs["blogpost_id"] == "bp-1"
    assert cs["chunk_index"] == 0
    assert cs["chunk_text"] == mock_chunks[0].chunk_text
    assert len(cs["chunk_vector"]) == 384


async def test_upgrade_already_done_raises(
    elastic_with_mocked_embeddings: tuple[
        ElasticService, BlogpostsEmbeddingsMock,
    ],
):
    """Повторный upgrade 3→5 падает — _v3 уже существует."""
    es, mock = elastic_with_mocked_embeddings

    mock_vector = [0.1] * 384
    mock.set_result("bp-1", title_vector=mock_vector)

    await es.migrations.upgrade(current="1", to="5")

    with pytest.raises(BadRequestError):
        await es.migrations.upgrade(current="3", to="5")


# ── downgrade ──────────────────────────────────────────────────────────────


async def test_downgrade_removes_vectors(
    elastic_with_mocked_embeddings: tuple[
        ElasticService, BlogpostsEmbeddingsMock,
    ],
):
    """downgrade 5→3 удаляет _v3 и индекс чанков, восстанавливает _v2 без векторов."""
    es, mock = elastic_with_mocked_embeddings
    cfg = es._config

    mock_vector = [0.1] * 384
    mock.set_result("bp-1", title_vector=mock_vector)

    await es.migrations.upgrade(current="1", to="5")

    alias = cfg.es_blogposts_index_name
    v2 = f"{alias}_v2"
    v3 = f"{alias}_v3"
    chunks_index = cfg.es_blogposts_text_chunks_index_name

    # Кладём данные через alias (попадают в _v3)
    await es.client.index(
        index=alias,
        id="bp-1",
        body={
            "title": "T",
            "text": "X",
            "tags": ["a"],
        },
        refresh=True,
    )

    await es.migrations.downgrade(current="5", to="3")

    # _v3 удалён, _v2 существует
    assert not await es.client.indices.exists(index=v3)
    assert await es.client.indices.exists(index=v2)

    # Индекс чанков удалён
    assert not await es.client.indices.exists(index=chunks_index)

    # Alias указывает на _v2
    alias_info = await es.client.indices.get(index=alias)
    assert v2 in alias_info

    # title_vector отсутствует в маппинге _v2
    mapping_resp = await es.client.indices.get_mapping(index=alias)
    mapping = next(iter(mapping_resp.body.values()))
    props = mapping["mappings"]["properties"]
    assert "title_vector" not in props

    # Данные сохранились (без векторов)
    search_result = await es.client.search(
        index=alias,
        body={"query": {"match_all": {}}},
    )
    hits = search_result["hits"]["hits"]
    assert len(hits) == 1
    assert hits[0]["_source"]["title"] == "T"
    assert "title_vector" not in hits[0]["_source"]


async def test_downgrade_idempotent(
    elastic_with_mocked_embeddings: tuple[
        ElasticService, BlogpostsEmbeddingsMock,
    ],
):
    """Повторный downgrade не падает."""
    es, mock = elastic_with_mocked_embeddings

    mock_vector = [0.1] * 384
    mock.set_result("bp-1", title_vector=mock_vector)

    await es.migrations.upgrade(current="1", to="5")
    await es.migrations.downgrade(current="5", to="3")
    # Повторный вызов не должен падать
    await es.migrations.downgrade(current="5", to="3")


# ── guard ──────────────────────────────────────────────────────────────────


async def test_upgrade_without_v2_raises(
    test_config: Config,
):
    """upgrade 3→5 без _v2 падает — 0003 не была применена."""
    cfg = Config(**{
        **test_config.model_dump(),
        "es_blogposts_index_name": f"{test_config.es_blogposts_index_name}_0005_nov2",
        "es_blogposts_text_chunks_index_name": (
            f"{test_config.es_blogposts_text_chunks_index_name}_0005_nov2"
        ),
    })
    es = ElasticService(cfg)
    try:
        # Применяем 0002 + 0003, затем удаляем _v2
        await es.migrations.upgrade(current="1", to="3")
        v2 = f"{cfg.es_blogposts_index_name}_v2"
        await es.client.indices.delete(index=v2)

        with pytest.raises(ValueError, match="не была применена"):
            await es.migrations.upgrade(current="3", to="5")
    finally:
        await es.migrations.delete_indices()
        await es.close()
