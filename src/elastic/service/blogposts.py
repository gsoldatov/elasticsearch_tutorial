from typing import TYPE_CHECKING

from elasticsearch.helpers import async_bulk

from src.elastic.base import ElasticBlogpostsServiceBase
from src.models.blogpost import Blogpost

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticBlogpostsService(ElasticBlogpostsServiceBase):
    """Операции с блогпостами в ES: индексация."""

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
