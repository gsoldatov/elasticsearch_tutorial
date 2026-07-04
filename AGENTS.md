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
    - `elastic/` — Elastic client, configuration and related utilities;
    - `middleware/` — middleware dir;
    - `models/` — Pydantic models (config, document schemas);
    - `routes/` — route handlers with sub-routers per resource;
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
- db repository:
    - convert returned data to Pydantic models;
    - are decorated with `internal_validation`, when they return Pydantic model objects;
- routes:
    - OpenAPI docs for the route must correctly reflect all of its responses;
    - 404 responses are explicitly handled by the route handlers;
- Pydantic models live in `src/models/`, SQLAlchemy ORM models in `src/db/models.py`;
- error messages, comments (including separation comments) and README are in Russian; code is in English;

- tests:
    - write test cases as functions;
    - test case order (where applicable): errors (validation, network, etc.) -> business logic errors -> edge cases -> happy path;
    - assert errors are in Russian, rest can be in English;


# Commands
## When App Server is Run Locally
### DB Management
```bash
# Create app user & DB
uv run src/db/scripts/app_db.py

# Run Alembic migrations
uv run alembic -c src/db/alembic/alembic.ini upgrade head

# Ingest test data
uv run src/db/scripts/ingest_data.py

# Drop and create again app user & DB
uv run src/db/scripts/app_db.py --delete-existing
```


### Elastic Management
```bash
# Create document index
uv run src/elastic/scripts/create_index.py

# Ingest documents into index (only after they're added to DB)
uv run src/elastic/scripts/ingest_es_data.py

# Delete document index
uv run src/elastic/scripts/delete_index.py
```


### Testing
```bash
# Run all tests (requires `docker compose up`)
uv run pytest
```


## When App Server is Run in Docker
Commands are run after `docker compose up` is done.


### DB Management
```bash
# Create app user & DB
docker compose exec api uv run src/db/scripts/app_db.py

# Run Alembic migrations
docker compose exec api uv run alembic -c src/db/alembic/alembic.ini upgrade head

# Ingest test data
docker compose exec api uv run src/db/scripts/ingest_data.py

# Drop and create again app user & DB
docker compose exec api uv run src/db/scripts/app_db.py --delete-existing
```


### Elastic Management
```bash
# Create document index
docker compose exec api uv run src/elastic/scripts/create_index.py

# Ingest documents into index (only after they're added to DB)
docker compose exec api uv run src/elastic/scripts/ingest_es_data.py

# Delete document index
docker compose exec api uv run src/elastic/scripts/delete_index.py
```


### Testing
```bash
# Run all tests (requires `docker compose up`)
docker compose exec api uv run pytest
```