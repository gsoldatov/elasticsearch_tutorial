from typing import TYPE_CHECKING

from src.elastic.service.migrations.base import ElasticMigrationsBase
from src.elastic.service.migrations.revisions.base import RevisionBase
from src.elastic.service.migrations.revisions.r_0001_documents import (
    Revision0001Documents,
)
from src.elastic.service.migrations.revisions.r_0002_blogposts import (
    Revision0002Blogposts,
)
from src.elastic.service.migrations.revisions.r_0003_blogpost_tags_subfield import (
    Revision0003BlogpostTagsSubfield,
)
from src.elastic.service.migrations.revisions.r_0004_sales import (
    Revision0004Sales,
)
from src.elastic.service.migrations.revisions.r_0005_blogpost_vectors import (
    Revision0005BlogpostVectors,
)

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticMigrations(ElasticMigrationsBase):
    """Фасад для запуска миграций ES."""

    def __init__(self, es: "ElasticService") -> None:
        self._es = es
        self._revisions: list[RevisionBase] = [
            Revision0001Documents(es),
            Revision0002Blogposts(es),
            Revision0003BlogpostTagsSubfield(es),
            Revision0004Sales(es),
            Revision0005BlogpostVectors(es),
        ]

    async def upgrade(self, current: str, to: str) -> None:
        """Применяет ревизии от current до to (не включительно → включительно)."""
        current_idx = self._resolve_revision(current)
        to_idx = self._resolve_revision(to)
        if current_idx >= to_idx:
            return
        for i in range(current_idx, to_idx):
            await self._revisions[i].upgrade()

    async def downgrade(self, current: str, to: str) -> None:
        """Откатывает ревизии от current до to в обратном порядке."""
        current_idx = self._resolve_revision(current)
        to_idx = self._resolve_revision(to)
        if current_idx <= to_idx:
            return
        for i in range(current_idx - 1, to_idx - 1, -1):
            await self._revisions[i].downgrade()

    async def delete_indices(self) -> None:
        """Удаляет все индексы и связанные pipelines."""
        for index_name in self._es._config.es_indices.values():
            # Удаление индексов по паттерну (позволяет удалять
            # версионированные индексы и их алиасы)
            await self._es.client.options(ignore_status=[404]).indices.delete(
                index=f"{index_name}*",
                allow_no_indices=True,
                expand_wildcards="all",
            )
        # Удаление ingest pipeline (после индексов — снимаем ссылки)
        pipeline_name = f"{self._es._config.es_blogposts_index_name}_pipeline"
        await self._es.client.options(ignore_status=[404]).ingest.delete_pipeline(
            id=pipeline_name,
        )

    def _resolve_revision(self, revision: str) -> int:
        """Преобразует 'base' / 'head' / число в индекс списка ревизий.

        'base' → 0, 'head' → len(revisions), число N → N (1-based).
        """
        if revision == "base":
            return 0
        if revision == "head":
            return len(self._revisions)
        try:
            num = int(revision)
        except ValueError:
            raise ValueError(
                f"Неизвестная ревизия: {revision}. "
                f"Ожидается 'base', 'head' или номер ревизии."
            )
        if num < 1 or num > len(self._revisions):
            raise ValueError(
                f"Ревизия {num} вне диапазона [1, {len(self._revisions)}]."
            )
        return num
