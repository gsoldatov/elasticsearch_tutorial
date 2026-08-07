"""Тесты BlogpostsEmbeddings."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.elastic import ElasticService
from src.exceptions import EmbeddingsNetworkError
from src.models.blogpost import BlogpostTextChunk


async def test_get_embeddings(elastic_service: ElasticService):
    """Эмбеддинги для заголовка и текста: размерность 384, chunk_index."""
    title_vector, chunks = await elastic_service.blogposts._embeddings.get_embeddings(
        blogpost_id="test-1",
        title="тестовый заголовок",
        text="тестовый текст блогпоста для проверки чанкинга. " * 5,
    )

    assert title_vector is not None
    assert len(title_vector) == 384
    assert all(isinstance(v, float) for v in title_vector)

    assert len(chunks) > 0
    for idx, chunk in enumerate(chunks):
        assert isinstance(chunk, BlogpostTextChunk)
        assert chunk.blogpost_id == "test-1"
        assert len(chunk.chunk_vector) == 384
        assert chunk.chunk_index == idx


async def test_no_args(elastic_service: ElasticService):
    """Без аргументов: оба None."""
    title_vector, chunks = await elastic_service.blogposts._embeddings.get_embeddings(
        blogpost_id="test-2",
    )

    assert title_vector is None
    assert chunks == []


async def test_empty_text_no_chunks(elastic_service: ElasticService):
    """Пустой текст не создаёт чанков."""
    _title_vector, chunks = await elastic_service.blogposts._embeddings.get_embeddings(
        blogpost_id="test-3",
        text="",
    )

    assert chunks == []


async def test_nonexistent_host_raises_embeddings_error(test_config):
    """Недоступный хост Ollama → EmbeddingsNetworkError."""
    from src.models.config import Config

    cfg = Config(**{
        **test_config.model_dump(),
        "ollama_host": "nonexistent-host.invalid",
        "ollama_port": 11434,
    })
    es = ElasticService(cfg)
    try:
        with pytest.raises(EmbeddingsNetworkError):
            await es.blogposts._embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )
    finally:
        await es.close()


async def test_connection_refused_raises_embeddings_error(test_config):
    """Отказ в соединении → EmbeddingsNetworkError."""
    from src.models.config import Config

    cfg = Config(**{
        **test_config.model_dump(),
        "ollama_port": 19999,  # порт, на котором никто не слушает
    })
    es = ElasticService(cfg)
    try:
        with pytest.raises(EmbeddingsNetworkError):
            await es.blogposts._embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )
    finally:
        await es.close()


async def test_timeout_raises_embeddings_error(elastic_service: ElasticService):
    """Таймаут httpx → EmbeddingsNetworkError."""
    # Форсируем создание клиента до патча
    client = elastic_service.blogposts._embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts._embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )
