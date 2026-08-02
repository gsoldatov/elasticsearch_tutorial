from datetime import datetime, timezone
from typing import TYPE_CHECKING

from elasticsearch import ConflictError
from elasticsearch import NotFoundError as EsNotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticBlogpostsServiceBase
from src.exceptions import NotFoundException, UpdateConflict, internal_validation
from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostSearchResult, BlogpostUpdate

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticBlogpostsService(ElasticBlogpostsServiceBase):
    """Операции с блогпостами в ES: индексация, CRUD."""

    def __init__(self, _es: "ElasticService") -> None:
        self._es = _es

    @property
    def client(self):
        return self._es.client

    async def index_blogposts(self, blogposts: list[Blogpost]) -> None:
        """Массовая индексация блогпостов.

        id модели используется как ES _id, в _source попадают
        все поля кроме id.
        """
        actions = [
            {
                "_index": self._es._config.es_blogposts_index_name,
                "_id": bp.id,
                "_source": bp.model_dump(mode="json", exclude={"id"}),
            }
            for bp in blogposts
        ]
        await async_bulk(self.client, actions, refresh=self._es._refresh)

    @internal_validation
    async def create(self, data: BlogpostCreate) -> Blogpost:
        """Создание блогпоста. Если id не передан — ES генерирует авто-id.
        Если id передан и уже существует — 409."""
        index = self._es._config.es_blogposts_index_name
        body = data.model_dump(mode="json", exclude_none=True)
        doc_id = body.pop("id", None)
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

        created = await self.client.get(index=index, id=response["_id"])
        return Blogpost(id=created["_id"], **created["_source"])

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
        """Частичное обновление блогпоста с optimistic lock (до 3 попыток)."""
        index = self._es._config.es_blogposts_index_name
        body = data.model_dump(mode="json", exclude_none=True)
        if "updated_at" not in body:
            body["updated_at"] = datetime.now(timezone.utc)

        try:
            response = await self.client.update(
                index=index,
                id=blogpost_id,
                doc=body,
                retry_on_conflict=2,
                source=True,
            )
        except ConflictError:
            raise UpdateConflict(
                "Конфликт версий документа. Попробуйте позже."
            ) from None
        except EsNotFoundError:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")

        return Blogpost(
            id=response["_id"],
            **response["get"]["_source"],
        )

    async def delete(self, blogpost_id: str) -> None:
        """Удаление блогпоста. Идемпотентно: не найдено → не ошибка."""
        index = self._es._config.es_blogposts_index_name
        await self.client.options(ignore_status=[404]).delete(
            index=index,
            id=blogpost_id,
            refresh=self._es._refresh,
        )

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
