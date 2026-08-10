from datetime import datetime, timezone
from re import sub as re_sub
from typing import TYPE_CHECKING

import asyncio

from elasticsearch import ConflictError
from elasticsearch import NotFoundError as EsNotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticBlogpostsServiceBase
from src.elastic.service.blogposts_embeddings import BlogpostsEmbeddings
from src.exceptions import (
    NotFoundException,
    UpdateConflict,
    internal_validation,
)
from src.models.blogpost import (
    Blogpost,
    BlogpostCreate,
    BlogpostSearchResult,
    BlogpostUpdate,
)

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticBlogpostsService(ElasticBlogpostsServiceBase):
    """Операции с блогпостами в ES: индексация, CRUD."""

    def __init__(self, _es: "ElasticService") -> None:
        self._es = _es
        self._embeddings = BlogpostsEmbeddings(_es)

    @property
    def embeddings(self) -> BlogpostsEmbeddings:
        return self._embeddings

    @property
    def client(self):
        return self._es.client

    # ── CRUD ────────────────────────────────────────────────────────────

    async def index_blogposts(self, blogposts: list[Blogpost]) -> None:
        """Массовая индексация блогпостов с эмбеддингами.

        Для каждого поста получает эмбеддинги заголовка и текста,
        затем вставляет документы в индекс блогпостов (с title_vector)
        и чанки текста в индекс чанков.
        """
        blogpost_actions: list[dict] = []
        chunk_actions: list[dict] = []

        for bp in blogposts:
            title_vector, chunks = await self.embeddings.get_embeddings(
                bp.id, title=bp.title, text=bp.text,
            )

            doc = bp.model_dump(mode="json", exclude={"id"})
            if title_vector is not None:
                doc["title_vector"] = title_vector

            blogpost_actions.append({
                "_index": self._es._config.es_blogposts_index_name,
                "_id": bp.id,
                "_source": doc,
            })

            for chunk in chunks:
                chunk_actions.append({
                    "_index": self._es._config.es_blogposts_text_chunks_index_name,
                    "_source": chunk.model_dump(mode="json"),
                })

        if blogpost_actions:
            await async_bulk(
                self.client, blogpost_actions,
                refresh=self._es._refresh,
            )
        if chunk_actions:
            await async_bulk(
                self.client, chunk_actions,
                refresh=self._es._refresh,
            )

    @internal_validation
    async def create(self, data: BlogpostCreate) -> Blogpost:
        """Создание блогпоста с эмбеддингами.

        Двухфазный подход:
        1. Индексация без векторов → получение _id.
        2. Получение эмбеддингов для заголовка и текста.
        3. Частичное обновление документа с title_vector, если получен.
        4. Индексация чанков текста в индекс blogposts_text_chunks.
        """
        index = self._es._config.es_blogposts_index_name
        chunks_index = self._es._config.es_blogposts_text_chunks_index_name
        body = data.model_dump(mode="json", exclude_none=True)
        doc_id = body.pop("id", None)

        # Если updated_at не передан — выставляем сейчас,
        # чтобы не делать лишний get после индексации
        if "updated_at" not in body:
            body["updated_at"] = datetime.now(timezone.utc)

        args: dict = {"index": index, "body": body}
        if doc_id is not None:
            args["id"] = doc_id
            args["op_type"] = "create"

        try:
            response = await self.client.index(
                **args, refresh=self._es._refresh,
            )
        except ConflictError:
            raise UpdateConflict(
                f"Блогпост с id '{doc_id}' уже существует."
            ) from None

        created_id = response["_id"]

        # Получение эмбеддингов
        title_vector, chunks = await self.embeddings.get_embeddings(
            created_id, title=data.title, text=data.text,
        )

        # Частичное обновление документа с title_vector
        if title_vector is not None:
            await self.client.update(
                index=index,
                id=created_id,
                doc={"title_vector": title_vector},
                refresh=self._es._refresh,
            )

        # Индексация чанков текста
        if chunks:
            chunk_actions = [
                {
                    "_index": chunks_index,
                    "_source": chunk.model_dump(mode="json"),
                }
                for chunk in chunks
            ]
            await async_bulk(
                self.client, chunk_actions,
                refresh=self._es._refresh,
            )

        return Blogpost(id=created_id, **body)

    @internal_validation
    async def get(self, blogpost_id: str) -> Blogpost:
        """Получение блогпоста по id."""
        index = self._es._config.es_blogposts_index_name
        try:
            response = await self.client.get(index=index, id=blogpost_id)
        except EsNotFoundError:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")
        return Blogpost(id=response["_id"], **response["_source"])

    @internal_validation
    async def update(self, blogpost_id: str, data: BlogpostUpdate) -> Blogpost:
        """Частичное обновление блогпоста с optimistic lock (до 3 попыток).

        Эмбеддинги вычисляются до обновления ES (fail-fast):
        если Ollama недоступен, документ не затрагивается.
        """
        index = self._es._config.es_blogposts_index_name
        chunks_index = self._es._config.es_blogposts_text_chunks_index_name

        # Вычисление эмбеддингов до обновления ES (fail-fast)
        title_vector: list[float] | None = None
        chunks: list = []
        if data.title is not None or data.text is not None:
            title_vector, chunks = await self.embeddings.get_embeddings(
                blogpost_id, title=data.title, text=data.text,
            )

        body = data.model_dump(mode="json", exclude_none=True)
        if "updated_at" not in body:
            body["updated_at"] = datetime.now(timezone.utc)
        if title_vector is not None:
            body["title_vector"] = title_vector

        try:
            response = await self.client.update(
                index=index,
                id=blogpost_id,
                doc=body,
                source=True,
            )
        except ConflictError:
            raise UpdateConflict(
                "Конфликт версий документа. Попробуйте позже."
            ) from None
        except EsNotFoundError:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")

        # Замена чанков текста
        if chunks:
            await self.client.options(ignore_status=[404]).delete_by_query(
                index=chunks_index,
                body={
                    "query": {"term": {"blogpost_id": blogpost_id}},
                },
                refresh=self._es._refresh,
            )
            chunk_actions = [
                {
                    "_index": chunks_index,
                    "_source": chunk.model_dump(mode="json"),
                }
                for chunk in chunks
            ]
            await async_bulk(
                self.client, chunk_actions,
                refresh=self._es._refresh,
            )

        return Blogpost(
            id=response["_id"],
            **response["get"]["_source"],
        )

    async def delete(self, blogpost_id: str) -> None:
        """Удаление блогпоста и его чанков. Идемпотентно: не найдено → не ошибка."""
        index = self._es._config.es_blogposts_index_name
        chunks_index = self._es._config.es_blogposts_text_chunks_index_name
        await self.client.options(ignore_status=[404]).delete(
            index=index,
            id=blogpost_id,
            refresh=self._es._refresh,
        )
        await self.client.options(ignore_status=[404]).delete_by_query(
            index=chunks_index,
            body={
                "query": {"term": {"blogpost_id": blogpost_id}},
            },
            refresh=self._es._refresh,
        )

    # ── Full-text search ────────────────────────────────────────────────────────────

    @internal_validation
    async def search(
        self,
        query: str,
        *,
        min_time: datetime | None = None,
        max_time: datetime | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> BlogpostSearchResult:
        """
        Полнотекстовый поиск блогпостов с фильтрами и пагинацией.
        """
        index = self._es._config.es_blogposts_index_name
        must: list[dict] = [
            {
                "multi_match": {
                    "query": query,
                    # поля, по которым ведется поиск
                    "fields": ["title^3", "text"],
                    # стратегия объединения результатов - берется лучшее значения
                    # (используется по умолчанию, но указана явно)
                    "type": "best_fields",
                    # поиск документов по любому из терминов запроса
                    # (используется по умолчанию, но указана явно)
                    "operator": "or",
                    # нечеткий поиск с динамическим количеством ошибок,
                    # в зависимости от длина слова
                    # (используется по умолчанию, но указана явно)
                    "fuzziness": "AUTO",
                    # количество начальных символов, которые не учитываются в нечетком поиске
                    "prefix_length": 2,
                },
            },
        ]

        body: dict = {
            "query": {"bool": {"must": must}},
            "from": (page - 1) * per_page,
            "size": per_page,
            "track_total_hits": True,
            "sort": [{"updated_at": "desc"}],
        }

        # Фильтр по диапазону updated_at — документы вне диапазона исключаются
        if min_time is not None or max_time is not None:
            range_filter: dict = {}
            if min_time is not None:
                range_filter["gte"] = min_time.isoformat()
            if max_time is not None:
                range_filter["lte"] = max_time.isoformat()
            body["query"]["bool"]["filter"] = [
                {"range": {"updated_at": range_filter}},
            ]

        # Фильтр по тегам: should с minimum_should_match: 1 —
        # документ должен иметь хотя бы один из указанных тегов,
        # а совпадение по нескольким тегам повышает score
        if tags:
            body["query"]["bool"]["should"] = [
                {"term": {"tags": tag}} for tag in tags
            ]
            body["query"]["bool"]["minimum_should_match"] = 1

        response = await self.client.search(index=index, body=body)

        total = response["hits"]["total"]["value"]
        if total == 0:
            raise NotFoundException("Блогпосты по заданному запросу не найдены")

        items = [
            Blogpost(id=hit["_id"], **hit["_source"])
            for hit in response["hits"]["hits"]
        ]
        return BlogpostSearchResult(items=items, total=total)


    async def search_tags(self, q: str) -> list[str]:
        """Префиксный поиск по тегам. Возвращает уникальные теги."""
        # Нормализация запроса: пробелы/табы → '_',
        # остальные не-букво-цифры (кроме '_') удаляются
        q = re_sub(r"[^\w]", "", q.replace("\t", "_").replace(" ", "_"))

        # Case-insensitive префиксный регекс для фильтрации агрегации.
        # Lucene-регекс не поддерживает (?i) — строим через классы символов.
        _re_chars: list[str] = []
        for c in q:
            if c.isalpha():
                _re_chars.append(f"[{c.lower()}{c.upper()}]")
            elif c in ".?+*|{}[]()\"\\#@&<>~":
                _re_chars.append("\\" + c)
            else:
                _re_chars.append(c)
        _include_re = "".join(_re_chars) + ".*"

        index = self._es._config.es_blogposts_index_name

        body: dict = {
            "query": {
                "match_bool_prefix": {
                    "tags._as_you_type": {
                        "query": q,
                    },
                },
            },
            "aggs": {
                "unique_tags": {
                    "terms": {
                        "field": "tags",
                        "include": _include_re,
                        "size": 10,
                    },
                },
            },
            "size": 0,
        }

        response = await self.client.search(index=index, body=body)

        total = response["hits"]["total"]["value"]
        if total == 0:
            raise NotFoundException("Теги по заданному запросу не найдены")

        buckets = response["aggregations"]["unique_tags"]["buckets"]
        return sorted(bucket["key"] for bucket in buckets)

    # ── Vector search ────────────────────────────────────────────────────────

    @internal_validation
    async def vector_search(
        self, query: str, size: int = 20,
    ) -> list[Blogpost]:
        """Векторный поиск блогпостов: KNN по title_vector и chunk_vector
        с линейным слиянием (title имеет вес 3x против text).

        Ограничения текущей реализации:
        - Поиск полным перебором (brute-force): ES 7.17 не поддерживает
          индексирование dense_vector (HNSW добавлен в 8.x), поэтому
          каждый запрос сканирует все документы индекса.
        - Два запроса к ES (title + text chunks) вместо одного —
          увеличивает latency.
        - Документы без title_vector исключаются из title-результатов
          через exists-фильтр (cosineSimilarity на отсутствующем поле
          вызывает runtime error).
        """
        index = self._es._config.es_blogposts_index_name
        chunks_index = self._es._config.es_blogposts_text_chunks_index_name

        # Получаем эмбеддинг поискового запроса
        query_vector = await self.embeddings.embed_query(query)

        # ── Title-поиск: script_score по title_vector ─────────────────────
        # ES 7.17: dense_vector не индексируется (нет HNSW),
        # поэтому поиск полным перебором через script_score.
        # cosineSimilarity возвращает [-1, 1]; отрицательные скоры
        # исключаются ES автоматически — это корректно, т.к. они
        # соответствуют семантически нерелевантным документам.
        # +1.0 не добавляем: линейный сдвиг не меняет порядок сортировки.
        title_body = {
            "query": {
                "script_score": {
                    # exists-фильтр: скрипт выполняется только для документов,
                    # у которых есть поле title_vector — без него
                    # cosineSimilarity упадёт с runtime error
                    "query": {"exists": {"field": "title_vector"}},
                    "script": {
                        "source": (
                            "cosineSimilarity("
                            "params.query_vector, 'title_vector'"
                            ")"
                        ),
                        "params": {"query_vector": query_vector},
                    },
                },
            },
            "size": size * 5,
            "_source": True,
        }

        # ── Text-поиск: script_score по chunk_vector с collapse ────────────
        # collapse по blogpost_id оставляет один хит на документ
        # с максимальным _score среди его чанков — это и есть
        # «best score per document» для текста.
        text_body = {
            "query": {
                "script_score": {
                    "query": {"exists": {"field": "chunk_vector"}},
                    "script": {
                        "source": (
                            "cosineSimilarity("
                            "params.query_vector, 'chunk_vector'"
                            ")"
                        ),
                        "params": {"query_vector": query_vector},
                    },
                },
            },
            "collapse": {"field": "blogpost_id"},
            "size": size * 5,
            "_source": False,
        }

        title_resp, text_resp = await asyncio.gather(
            self.client.search(index=index, body=title_body),
            self.client.search(index=chunks_index, body=text_body),
        )

        # ── Извлечение скоров ─────────────────────────────────────────────
        title_scores: dict[str, float] = {}
        for hit in title_resp["hits"]["hits"]:
            title_scores[hit["_id"]] = hit["_score"] or 0.0

        text_scores: dict[str, float] = {}
        for hit in text_resp["hits"]["hits"]:
            blogpost_id = hit["fields"]["blogpost_id"][0]
            text_scores[blogpost_id] = hit["_score"] or 0.0

        # ── Линейное слияние: final = 3 * title_score + text_score ───────
        # Скоры из обоих запросов — чистый cosineSimilarity в [-1, 1],
        # сравнимы напрямую. Title имеет вес 3x.
        # Документы с отрицательным косинусом уже исключены ES.
        all_ids: set[str] = set(title_scores) | set(text_scores)
        fused: list[tuple[str, float]] = []
        for doc_id in all_ids:
            t_score = title_scores.get(doc_id, 0.0)
            c_score = text_scores.get(doc_id, 0.0)
            fused.append((doc_id, 3 * t_score + c_score))

        fused.sort(key=lambda item: item[1], reverse=True)
        top_ids = [doc_id for doc_id, _ in fused[:size]]

        if not top_ids:
            return []

        # ── Получение полных документов ───────────────────────────────────
        # mget не гарантирует порядок — восстанавливаем вручную;
        # null-документы (удалённые между запросами) отфильтровываем.
        mget_resp = await self.client.mget(
            index=index,
            body={"ids": top_ids},
        )

        doc_map: dict[str, dict] = {}
        for doc in mget_resp["docs"]:
            if doc["found"]:
                doc_map[doc["_id"]] = doc["_source"]

        return [
            Blogpost(id=doc_id, **doc_map[doc_id])
            for doc_id in top_ids
            if doc_id in doc_map
        ]
