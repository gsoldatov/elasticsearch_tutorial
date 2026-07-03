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


# Project Structure
- `src/`:
    - `app.py` — FastAPI application factory;
    - `config.py` — loads and validates config from `.env` via Pydantic Settings;
    - `db/` — SQLAlchemy ORM models, Alembic migrations, repository layer, admin scripts:
        - `alembic/` — Alembic migrations;
        - `repository/` — repository classes (facade `Repository` + per-entity repositories);
    - `middleware/` — middleware dir;
    - `models/` — Pydantic models (config, document schemas);
    - `routes/` — route handlers with sub-routers per resource;
    - `services/` — services (ES client);
- `tests/`:
    - `conftest.py` — shared fixtures:
        - config and test database are module-scoped;
        - test app and client are test-scoped;
        - db data is truncated after each test;
    - `mocks/`:
        - data generation classes;
        - db operations;
        - elastic service mock for app + db tests;
    - `tests/`: test cases mirroring `src/` structure;

# Patterns and Implementation Guidelines
- `.env` file is a single source of configuration for all project items;
- use absolute imports and update sys.path in executable files;
- repository methods:
    - convert returned data to Pydantic models;
    - are decorated with `internal_validation`, when they return Pydantic model objects;
- Pydantic models live in `src/models/`, SQLAlchemy ORM models in `src/db/models.py`;
- error messages, comments and README are in Russian; code is in English;

- tests:
    - write test cases as functions;
    - test case order (where applicable): errors (validation, network, etc.) -> business logic errors -> edge cases -> happy path;
    - assert errors are in Russian, rest can be in English;


# Commands
```bash
# Run all tests (requires `docker compose up`)
uv run pytest tests/

# Run Alembic migrations
uv run alembic -c src/db/alembic/alembic.ini upgrade head
```