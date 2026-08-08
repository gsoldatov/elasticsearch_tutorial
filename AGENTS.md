# Overview
A tutorial project for Elasticsearch, which focuses on using its key features and integratins ES with a Python web app and a relational DB.

Stack used:
- Python 3.13 + uv;
- PostgreSQL 17;
- Elasticsearch 7.17;
- Ollama for embedding inference;
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
    - `elastic/` — Elastic client, configuration, Ollama interaction and related utilities;
    - `middleware/` — middleware dir;
    - `models/` — Pydantic models (config, document schemas);
    - `routes/` — route handlers with sub-routers per resource;
- `tests/`:
    - `conftest.py` — shared fixtures:
        - config and test database and ES indices are module-scoped;
        - test app and client are test-scoped;
        - db and ES data is truncated after each test;
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
- Pydantic vs SQLAlchemy classes:
    - Pydantic models live in `src/models/`, SQLAlchemy ORM models in `src/db/models.py`;
    - Pydantic classes have singular names (`Document`), SQLAlchemy classes have plural names (`Documents`);
- ElasticSearch:
    - service methods:
        - accept and return Pydantic models, where applicable;
        - are decorated with `internal_validation`, when they return Pydantic model objects;
    - migrations:
        - are managed by `ElasticMigrations` class available via `ElasticService.migrations`;
        - each migration revision is implemented as subclass of `RevisionBase`:
            - migrations must use index names from the app config available via parent `ElasticService` object;
            - `upgrade`:
                - should try to throw where applicable to reduce the risk of out of order errors;
                - new indices should use aliases, so that they could be updated in future revisions via reindex + alias change;
            - `downgrade`:
                - should try to be idempotent and allow partial rollback of the applied changes, so that it's possible to revert changes, if they didn't apply properly;
- Ollama container:
    - used for inferring embeddings of text data;
    - should be mocked in tests, except for the test cases that directly test interaction with it;
- error messages, comments (including separation comments) and README are in Russian; code is in English;

- tests:
    - write test cases as functions;
    - test case order (where applicable): errors (validation, network, etc.) -> business logic errors -> edge cases -> happy path;
    - test cases should use data generator classes to create test data, where needed;
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
# Run Elasticsearch migrations (create indices)
uv run src/elastic/scripts/migrate.py --current base --to head

# Ingest documents into index (only after they're added to DB)
uv run src/elastic/scripts/ingest_documents.py

# Delete all Elasticsearch indices
uv run src/elastic/scripts/delete_indices.py
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
# Run Elasticsearch migrations (create indices)
docker compose exec api uv run src/elastic/scripts/migrate.py --current base --to head

# Ingest documents into index (only after they're added to DB)
docker compose exec api uv run src/elastic/scripts/ingest_documents.py

# Delete all Elasticsearch indices
docker compose exec api uv run src/elastic/scripts/delete_indices.py
```


### Testing
```bash
# Run all tests (requires `docker compose up`)
docker compose exec api uv run pytest
```