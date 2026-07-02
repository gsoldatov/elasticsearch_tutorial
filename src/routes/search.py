from fastapi import APIRouter, Query, Request

from src.models import Document

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[Document])
async def search(
    request: Request,
    q: str = Query(min_length=1, description="Текстовый запрос"),
) -> list[Document]:
    """
    Поиск документов по тексту.
    Возвращает до 20 документов, упорядоченных по дате создания.
    """
    elastic_service = request.app.state.elastic_service
    repository = request.state.repository

    ids = await elastic_service.search(q)
    return await repository.document.get_by_ids(ids, limit=20)
