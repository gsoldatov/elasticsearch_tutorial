from fastapi import FastAPI

from src.routes import blogposts, documents, sales


def setup_routes(app: FastAPI) -> None:
    app.include_router(documents.router, prefix="/documents")
    app.include_router(blogposts.router, prefix="/blogposts")
    app.include_router(sales.router, prefix="/sales")
