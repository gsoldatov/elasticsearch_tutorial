from datetime import datetime, timezone
from typing import TYPE_CHECKING

from elasticsearch import ConflictError
from elasticsearch import NotFoundError as EsNotFoundError
from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticBlogpostsServiceBase
from src.exceptions import NotFoundException, UpdateConflict
from src.models.blogpost import Blogpost

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

    async def create(self, data: dict) -> Blogpost:
        """Создание блогпоста. Если id не передан — ES генерирует авто-id.
        Если id передан и уже существует — 409."""
        index = self._es._config.es_blogposts_index_name
        doc_id = data.pop("id", None)
        args: dict = {"index": index, "body": data}
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

    async def get(self, blogpost_id: str) -> Blogpost:
        """Получение блогпоста по id."""
        index = self._es._config.es_blogposts_index_name
        try:
            response = await self.client.get(index=index, id=blogpost_id)
        except EsNotFoundError:
            raise NotFoundException(f"Блогпост {blogpost_id} не найден")
        return Blogpost(id=response["_id"], **response["_source"])

    async def update(self, blogpost_id: str, data: dict) -> Blogpost:
        """Частичное обновление блогпоста с optimistic lock (до 3 попыток)."""
        index = self._es._config.es_blogposts_index_name
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc)

        try:
            response = await self.client.update(
                index=index,
                id=blogpost_id,
                doc=data,
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
