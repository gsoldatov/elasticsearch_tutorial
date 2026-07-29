from typing import TYPE_CHECKING

from src.elastic.service.migrations.base import ElasticMigrationsBase
from src.elastic.service.migrations.revisions.base import RevisionBase
from src.elastic.service.migrations.revisions.r_0001_documents import (
    Revision0001Documents,
)

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class ElasticMigrations(ElasticMigrationsBase):
    """Фасад для запуска миграций ES."""

    def __init__(self, es: "ElasticService") -> None:
        self._es = es
        self._revisions: list[RevisionBase] = [
            Revision0001Documents(es),
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
        """Удаляет все индексы, перечисленные в конфиге."""
        for index_name in self._es._config.es_indices.values():
            await self._es.client.options(ignore_status=[404]).indices.delete(
                index=index_name,
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
