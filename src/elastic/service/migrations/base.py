from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.elastic.service.migrations.revisions.base import RevisionBase


class ElasticMigrationsBase(ABC):
    """Абстрактный класс фасада миграций ES."""

    _revisions: list["RevisionBase"]

    @abstractmethod
    async def upgrade(self, current: str, to: str) -> None:
        """Применяет миграции от current до to."""

    @abstractmethod
    async def downgrade(self, current: str, to: str) -> None:
        """Откатывает миграции от current до to."""

    @abstractmethod
    async def delete_indices(self) -> None:
        """Удаляет все индексы, перечисленные в конфиге."""
