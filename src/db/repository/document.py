from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document as DocumentModel
from src.exceptions import NotFoundException, internal_validation
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
        """Удаляет документ по id."""
        stmt = delete(DocumentModel).where(DocumentModel.id == doc_id)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise NotFoundException(f"Document {doc_id} not found")
