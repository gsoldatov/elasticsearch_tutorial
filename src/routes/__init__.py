from fastapi import FastAPI

from src.routes import documents, search


def setup_routes(app: FastAPI) -> None:
    app.include_router(search.router)
    app.include_router(documents.router)
