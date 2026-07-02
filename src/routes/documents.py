from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["documents"])


@router.delete(
    "/documents/{doc_id}",
    status_code=204,
    response_class=Response,
)
async def delete_document(request: Request, doc_id: int) -> None:
    """Удаляет документ по id из БД и поискового индекса."""
    elastic_service = request.app.state.elastic_service
    repository = request.state.repository

    await repository.document.delete_by_id(doc_id)
    await elastic_service.delete(doc_id)
