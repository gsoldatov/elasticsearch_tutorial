# Overview
A simple project implementing a web app integration with a relational DB and an Elastic full-text search index.

Stack used:
- Python 3.13 + uv;
- PostgreSQL 17;
- Elasticsearch 9;
- FastAPI;
- SQLAlchemy2 + psycopg3 + alembic;
- Pydantic + Pydantic Settings;
- pytest;


# Architecture
- `.env` file is a single source of configuration for all project items;
- `src/app.py` — FastAPI application factory;
- `src/config.py` — loads and validates config from `.env` via Pydantic Settings;
- `src/db/` — SQLAlchemy ORM models, Alembic migrations, repository layer, admin scripts:
    - `alembic/` — Alembic migrations;
    - `repository/` — repository classes (facade `Repository` + per-entity repositories);
- `src/middleware/` — middleware dir;
- `src/models/` — Pydantic models (config, document schemas);
- `src/routes/` — route handlers with sub-routers per resource;
- `src/services/` — services (ES client);


# Patterns and Implementation Guidelines
- use absolute imports and update sys.path in executable files;
- repository methods:
    - return Pydantic models;
    - are decorated with `internal_validation`;
- Pydantic models live in `src/models/`, SQLAlchemy ORM models in `src/db/models.py`;
- error messages, comments and README are in Russian; code is in English;

- tests:
    - placed in `tests/tests` directory and follow project's structure:
        - app tests tests use a temporary DB (via Docker) and mock ES client;
 