"""Тесты BlogpostsEmbeddings."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from ollama import ResponseError

from src.elastic import ElasticService
from src.exceptions import EmbeddingsNetworkError
from src.models.blogpost import BlogpostTextChunk


# ══════════════════════════════════════════════════════════════════════════════
# get_embeddings
# ══════════════════════════════════════════════════════════════════════════════


async def test_get_embeddings(elastic_service: ElasticService):
    """Эмбеддинги для заголовка и текста: размерность 384, chunk_index."""
    title_vector, chunks = await elastic_service.blogposts.embeddings.get_embeddings(
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
    title_vector, chunks = await elastic_service.blogposts.embeddings.get_embeddings(
        blogpost_id="test-2",
    )

    assert title_vector is None
    assert chunks == []


async def test_empty_text_no_chunks(elastic_service: ElasticService):
    """Пустой текст не создаёт чанков."""
    _title_vector, chunks = await elastic_service.blogposts.embeddings.get_embeddings(
        blogpost_id="test-3",
        text="",
    )

    assert chunks == []


async def test_connect_error_raises_embeddings_error(
    elastic_service: ElasticService,
):
    """httpx.ConnectError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=httpx.ConnectError("connect error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )


async def test_connection_error_raises_embeddings_error(
    elastic_service: ElasticService,
):
    """ConnectionError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=ConnectionError("connection error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )


async def test_response_error_raises_embeddings_error(
    elastic_service: ElasticService,
):
    """ResponseError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=ResponseError("response error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )


async def test_timeout_raises_embeddings_error(elastic_service: ElasticService):
    """Таймаут httpx → EmbeddingsNetworkError."""
    # Форсируем создание клиента до патча
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.get_embeddings(
                blogpost_id="test-err",
                title="заголовок",
            )


# ══════════════════════════════════════════════════════════════════════════════
# embed_query
# ══════════════════════════════════════════════════════════════════════════════


async def test_embed_query_returns_384_dim_vector(
    elastic_service: ElasticService,
):
    """embed_query возвращает список из 384 float."""
    vector = await elastic_service.blogposts.embeddings.embed_query(
        "поисковый запрос",
    )

    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector)


async def test_embed_query_connect_error(
    elastic_service: ElasticService,
):
    """httpx.ConnectError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=httpx.ConnectError("connect error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.embed_query("запрос")


async def test_embed_query_connection_error(
    elastic_service: ElasticService,
):
    """ConnectionError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=ConnectionError("connection error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.embed_query("запрос")


async def test_embed_query_response_error(
    elastic_service: ElasticService,
):
    """ResponseError → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=ResponseError("response error")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.embed_query("запрос")


async def test_embed_query_timeout_raises_error(
    elastic_service: ElasticService,
):
    """Таймаут httpx → EmbeddingsNetworkError."""
    client = elastic_service.blogposts.embeddings._get_ollama_client()

    with patch.object(
        client._client, "request",
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    ):
        with pytest.raises(EmbeddingsNetworkError):
            await elastic_service.blogposts.embeddings.embed_query("запрос")
