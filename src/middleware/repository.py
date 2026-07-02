from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.repository import Repository


async def repository_middleware(request: Request, call_next):
    """
    Создаёт сессию БД и репозиторий на каждый запрос.
    При успешном выполнении запроса — коммитит изменения.
    При необработанном исключении — откатывает транзакцию.
    """
    engine = request.app.state.engine
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        request.state.repository = Repository(session)
        try:
            response = await call_next(request)
            await session.commit()
            return response
        except Exception:
            await session.rollback()
            raise
