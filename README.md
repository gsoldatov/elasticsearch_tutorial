# Описание
Набор упражнений по работе с Elasticsearch на Python + тестовое задание для компании А. Включает в себя:
- настройка полнотекстового, векторного и гибридного поиска + CRUD-операции в ES (`/blogposts/...`);
- запросы на аггрегацию данных (`/sales/...`);
- выполнение тестового задания, описанного [здесь](docs/prd.md), - веб-приложение, взаимодействующее с ES и реляционной СУБД (`/documents/...`).

Веб-сервис на FastAPI с хранением данных в PostgreSQL и/или поисковыми индексами в Elasticsearch. Эмбеддинги текста для векторного поиска генерируются моделью, работающей в контейнере Ollama.

Состояние проекта на момент сдачи тестового задания доступно [здесь](../../tree/submitted).



## Стек
- Python 3.13 + uv;
- FastAPI;
- httpx;
- Pydantic, Pydantic Settings;
- PostgreSQL 17, SQLAlchemy 2 (async), Alembic;
- Elasticsearch 7.17;
- Ollama.



## Структура проекта
```
src/
├── app.py              # Фабрика FastAPI-приложения
├── config.py           # Загрузка конфига из .env
├── db/
│   ├── models.py       # SQLAlchemy ORM-модели
│   ├── alembic/        # Миграции Alembic
│   ├── repository/     # Слой доступа к данным
│   └── scripts/        # Утилиты (создание БД, загрузка данных)
|
├── elastic/
│   ├── base.py         # Базовый класс Elasticsearch-сервиса
│   ├── scripts/        # Утилиты (запуск миграций, удаление индексов, загрузка тестовых данных)
│   └── service/        # Сервисные классы для взаимодействия с ES и миграции индексов
|
├── exceptions.py       # Исключения уровня приложения
├── main.py             # Точка входа dev-сервера
├── middleware/         # Middleware (ошибки и сессия БД)
├── models/             # Pydantic-модели
└── routes/
    ├── blogposts.py    # Упражения по настройке полнотекстового и векторного поиска + CRUD
    ├── documents.py    # Эндпоинты из тестового задания
    └── sales.py        # Упражения по аггрегирующим запросам в ES

tests/
├── conftest.py         # Фикстуры
├── mocks/              # Моки и утилиты для тестов
└── tests/              # Тесты, зеркалирующие структуру src/
```



## Допущения и технические решения (по тестовому заданию)
Некоторые требования ТЗ допускают неоднозначную трактовку относительно их реализации, соответствующие им решения перечислены ниже:

- **структура данных**:
    - БД:
        - `rubrics` - хранятся как ARRAY(TEXT), т.к. максимальная длина рубрик не указана;
        - `created_at` - исходные данные не содержат таймзоны, при загрузке им присваивается таймзона UTC;
    - индекс в ES:
        - `id` документа присутствует и как ключ, и как атрибут документа;
        - `created_at` не добавляется в индекс, т.к. ТЗ предполагает цепочку api > ES > api > DB при поиске данных (хотя можно было бы ограничиться одним запросом к ES);
        - при индексации `text` используется русский анализатор;

- **эндпоинт поиска**:
    - принимает поисковый запрос в качестве URL-параметра `q`;
    - тип поиска - `match_phrase` (совпадение по фразе с учетом порядка слов);
    - подходящие документы сортируются по УБЫВАНИЮ даты создания (в ТЗ не указан порядок сортировки);

- **эндпоинт удаления данных**:
    - возвращает 404, если документа нет в БД;
    - если документ отсутствует в ES, но есть в БД, вернет 204 (и удалит из БД).



# Настройка окружения для разработки (API, БД и ES в контейнерах)
```bash
# 1. Скопировать env-файл (изменив его, если требуется)
cp .env.example .env

# 2. Поднять сервисы (БД, Elasticsearch, API)
docker compose up

# 3. Создать пользователя и БД приложения
docker compose exec api uv run src/db/scripts/app_db.py

# 4. Применить миграции к БД приложения
docker compose exec api uv run alembic -c src/db/alembic/alembic.ini upgrade head

# 5. Создать индексы в ES
docker compose exec api uv run src/elastic/scripts/migrate.py --current base --to head
```

API доступен на `http://localhost:<BACKEND_PORT>`.



## Дополнительные команды
```bash
# Загрузить тестовые данные
## Documents (db скрипт должен быть запущен первым)
docker compose exec api uv run src/db/scripts/ingest_documents.py
docker compose exec api uv run src/elastic/scripts/ingest_documents.py

## Blogposts
docker compose exec api uv run src/elastic/scripts/ingest_blogposts.py --write-file-path data/blogposts.json

## Sales
docker compose exec api uv run src/elastic/scripts/ingest_sales.py --write-file-path data/sales.json

# Запустить тесты
docker compose exec api uv run pytest

# Пересоздать пользователя и БД приложения
docker compose exec api uv run src/db/scripts/app_db.py --delete-existing
docker compose exec api uv run alembic -c src/db/alembic/alembic.ini upgrade head

# Удалить и создать заново индексы в ES
docker compose exec api uv run src/elastic/scripts/delete_indices.py
docker compose exec api uv run src/elastic/scripts/migrate.py --current base --to head
```



# Настройка окружения для разработки (API развернуто локально, БД и ES - в контейнерах)
```bash
# 1. Установить зависимости
uv sync --dev

# 2. Скопировать env-файл (изменив его, если требуется)
cp .env.example .env

# 3. Поднять БД, Elasticsearch и Ollama
docker compose up db elasticsearch ollama

# 4. Создать пользователя и БД приложения
uv run src/db/scripts/app_db.py

# 5. Применить миграции к БД приложения
uv run alembic -c src/db/alembic/alembic.ini upgrade head

# 6. Создать индексы в ES
uv run src/elastic/scripts/migrate.py --current base --to head

# 7. Запустить сервер
uv run python src/main.py
```



## Дополнительные команды
Аналогичны командам для проекта, полностью поднятого в Docker, но без `docker compose exec api`. Для запуска тестов требуются контейнеры PostgreSQL, ES и Ollama.
