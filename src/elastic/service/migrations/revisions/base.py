from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.elastic.service import ElasticService


class RevisionBase(ABC):
    """Абстрактный класс ревизии ES."""

    def __init__(self, es: "ElasticService") -> None:
        self._es = es

    @abstractmethod
    async def upgrade(self) -> None:
        """Применяет ревизию."""

    @abstractmethod
    async def downgrade(self) -> None:
        """Откатывает ревизию."""
