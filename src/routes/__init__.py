from fastapi import FastAPI

from src.routes import blogposts, documents


def setup_routes(app: FastAPI) -> None:
    app.include_router(documents.router, prefix="/documents")
    app.include_router(blogposts.router, prefix="/blogposts")
