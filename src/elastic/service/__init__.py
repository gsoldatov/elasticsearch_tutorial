from elasticsearch import AsyncElasticsearch
from elastic_transport._node._http_httpx import HttpxAsyncHttpNode

from src.config import Config
from src.elastic.base import ElasticBlogpostsServiceBase, ElasticDocumentsServiceBase, ElasticServiceBase
from src.elastic.service.blogposts import ElasticBlogpostsService
from src.elastic.service.documents import ElasticDocumentsService
from src.elastic.service.migrations import ElasticMigrations
from src.elastic.service.migrations.base import ElasticMigrationsBase


class ElasticService(ElasticServiceBase):
    """Фасад для доступа к ES: клиент + документные операции + блогпосты + миграции."""

    def __init__(self, config: Config, *, refresh: bool = False) -> None:
        self._config = config
        self._refresh = refresh
        self._client: AsyncElasticsearch | None = None
        self._documents = ElasticDocumentsService(self)
        self._blogposts = ElasticBlogpostsService(self)
        self._migrations = ElasticMigrations(self)

    @property
    def documents(self) -> ElasticDocumentsServiceBase:
        return self._documents

    @property
    def blogposts(self) -> ElasticBlogpostsServiceBase:
        return self._blogposts

    @property
    def migrations(self) -> ElasticMigrationsBase:
        return self._migrations

    @property
    def client(self) -> AsyncElasticsearch:
        """Ленивое создание ES-клиента."""
        if self._client is None:
            self._client = AsyncElasticsearch(
                self._config.es_url,
                basic_auth=("elastic", self._config.es_superuser_password),
                node_class=HttpxAsyncHttpNode,
            )
        return self._client

    async def close(self) -> None:
        """Закрывает ES-клиент."""
        if self._client is not None:
            await self._client.close()
            self._client = None
