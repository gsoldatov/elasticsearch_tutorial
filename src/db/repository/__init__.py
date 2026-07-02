from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repository.document import DocumentRepository


class Repository:
    """Фасад для доступа ко всем репозиториям."""
    def __init__(self, session: AsyncSession) -> None:
        self.document = DocumentRepository(session)
