import asyncio
from typing import TYPE_CHECKING

import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ollama import AsyncClient, ResponseError
from tokenizers import Tokenizer

from src.elastic.base import BlogpostsEmbeddingsBase
from src.exceptions import EmbeddingsNetworkError
from src.models.blogpost import BlogpostTextChunk

if TYPE_CHECKING:
    from src.elastic.service import ElasticService

# ── Константы чанкинга ──────────────────────────────────────────────────

_CHUNK_SIZE = 512   # токенов на чанк
_CHUNK_OVERLAP = 52  # токенов перекрытия


class BlogpostsEmbeddings(BlogpostsEmbeddingsBase):
    """Получение эмбеддингов для заголовков и текстов блогпостов."""

    def __init__(self, _es: "ElasticService") -> None:
        self._es = _es
        self._ollama_client: AsyncClient | None = None
        self._tokenizer: Tokenizer | None = None

    def _get_ollama_client(self) -> AsyncClient:
        """Ленивое создание async-клиента Ollama."""
        if self._ollama_client is None:
            self._ollama_client = AsyncClient(
                host=self._es._config.ollama_url,
                timeout=self._es._config.ollama_timeout,
            )
        return self._ollama_client

    def _get_tokenizer(self) -> Tokenizer:
        """Ленивая загрузка токенизатора."""
        if self._tokenizer is None:
            self._tokenizer = Tokenizer.from_pretrained(
                self._es._config.ollama_tokenizer,
            )
        return self._tokenizer

    async def get_embeddings(
        self, blogpost_id: str, *,
        title: str | None = None, text: str | None = None,
    ) -> tuple[list[float] | None, list[BlogpostTextChunk]]:
        """Получает эмбеддинги для заголовка и текста блогпоста.

        Оба аргумента опциональны: если опущены — возвращается None
        и пустой список соответственно.
        """
        try:
            title_vector: list[float] | None = None
            if title is not None:
                title_vector = await self._embed_title(title)

            chunks: list[BlogpostTextChunk] = []
            if text is not None:
                chunks = await self._embed_text(blogpost_id, text)

            return title_vector, chunks
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            ResponseError,
            ConnectionError,
        ) as e:
            raise EmbeddingsNetworkError(str(e)) from e

    async def _embed_title(self, title: str) -> list[float]:
        """Получает эмбеддинг для заголовка."""
        client = self._get_ollama_client()
        response = await client.embed(
            model=self._es._config.ollama_model,
            input=title,
            keep_alive=self._es._config.ollama_keep_alive,
        )
        return list(response.embeddings[0])

    async def _embed_text(
        self, blogpost_id: str, text: str,
    ) -> list[BlogpostTextChunk]:
        """Чанкует текст и получает эмбеддинги для каждого чанка."""
        tokenizer = self._get_tokenizer()

        # Разбивка текста на чанки (размер в токена оценивается
        # с помощью токенизатора, использующегося моделью в Ollama)
        def token_len(t: str) -> int:
            return len(tokenizer.encode(t, add_special_tokens=False))

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP,
            length_function=token_len,
        )
        chunk_texts = await asyncio.to_thread(splitter.split_text, text)

        if not chunk_texts:
            return []

        client = self._get_ollama_client()
        model = self._es._config.ollama_model
        keep_alive = self._es._config.ollama_keep_alive
        batch_size = self._es._config.ollama_batch_size

        all_vectors: list[list[float]] = []

        # Отправка чанков батчами в Ollama для получения их эмбеддингов
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            response = await client.embed(
                model=model,
                input=batch,
                keep_alive=keep_alive,
            )
            all_vectors.extend(list(v) for v in response.embeddings)

        return [
            BlogpostTextChunk(
                blogpost_id=blogpost_id,
                chunk_index=idx,
                chunk_text=ct,
                chunk_vector=vec,
            )
            for idx, (ct, vec) in enumerate(zip(chunk_texts, all_vectors))
        ]
