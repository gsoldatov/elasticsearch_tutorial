from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document as DocumentModel
from src.exceptions import internal_validation
from src.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @internal_validation
    async def get_by_ids(self, ids: list[int], limit: int) -> list[Document]:
        """
        Возвращает документы по списку id,
        упорядоченные по дате создания по убыванию.
        """
        if not ids:
            return []
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.id.in_(ids))
            .order_by(DocumentModel.created_date.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [Document.model_validate(doc) for doc in result.scalars().all()]

    async def delete_by_id(self, doc_id: int) -> None:
        """Удаляет документ по id. Если документ не найден — ничего не делает."""
        stmt = delete(DocumentModel).where(DocumentModel.id == doc_id)
        await self._session.execute(stmt)
