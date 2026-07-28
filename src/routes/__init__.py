from fastapi import FastAPI

from src.routes import documents


def setup_routes(app: FastAPI) -> None:
    app.include_router(documents.router)
