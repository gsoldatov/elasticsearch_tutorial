# Поисковик по текстам документов
Тестовое задание для компании А.

Веб-сервис на FastAPI с хранением данных в PostgreSQL и поисковым индексом в Elasticsearch.


## Стек
- Python 3.13, uv;
- FastAPI, Pydantic, Pydantic Settings;
- PostgreSQL 17, SQLAlchemy 2 (async), Alembic;
- Elasticsearch 7.17.


## Допущения и технические решения
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


## Настройка окружения для разработки (API, БД и ES в контейнерах)
```bash
# 1. Скопировать env-файл (изменив его, если требуется)
cp .env.example .env

# 2. Поднять сервисы (БД, Elasticsearch, API)
docker compose up

# 3. Создать пользователя и БД приложения
docker compose exec api uv run src/db/scripts/app_db.py

# 4. Применить миграции
docker compose exec api uv run alembic -c src/db/alembic/alembic.ini upgrade head

# 5. Создать поисковый индекс
docker compose exec api uv run src/elastic/scripts/create_index.py
```

API доступен на `http://localhost:<BACKEND_PORT>`.


### Дополнительные команды
```bash
# Загрузить тестовые данные
docker compose exec api uv run src/db/scripts/ingest_data.py
docker compose exec api uv run src/elastic/scripts/ingest_es_data.py

# Запустить тесты
docker compose exec api uv run pytest

# Пересоздать пользователя и БД приложения
docker compose exec api uv run src/db/scripts/app_db.py --delete-existing
docker compose exec api uv run alembic -c src/db/alembic/alembic.ini upgrade head

# Удалить индекс в ES
docker compose exec api uv run src/elastic/scripts/delete_index.py
```



## Настройка окружения для разработки (API развернуто локально, БД и ES - в контейнерах)
```bash
# 1. Установить зависимости
uv sync --dev

# 2. Скопировать env-файл (изменив его, если требуется)
cp .env.example .env

# 3. Поднять БД и Elasticsearch
docker compose up db elasticsearch

# 4. Создать пользователя и БД приложения
uv run src/db/scripts/app_db.py

# 5. Применить миграции
uv run alembic -c src/db/alembic/alembic.ini upgrade head

# 6. Создать поисковый индекс
uv run src/elastic/scripts/create_index.py

# 7. Загрузить тестовые данные
uv run src/db/scripts/ingest_data.py
uv run src/elastic/scripts/ingest_es_data.py

# 8. Запустить сервер
uv run python src/main.py
```


### Дополнительные команды
```bash
# Загрузить тестовые данные
uv run src/db/scripts/ingest_data.py
uv run src/elastic/scripts/ingest_es_data.py

# Запустить тесты
uv run pytest

# Пересоздать пользователя и БД приложения
uv run src/db/scripts/app_db.py --delete-existing
uv run alembic -c src/db/alembic/alembic.ini upgrade head

# Удалить индекс в ES
uv run src/elastic/scripts/delete_index.py
```


## Структура проекта
```
src/
├── app.py              # Фабрика FastAPI-приложения
├── config.py           # Загрузка .env через Pydantic Settings
├── main.py             # Точка входа dev-сервера
├── models/             # Pydantic-модели (конфиг, схемы документов)
│   └── config.py
├── db/
│   ├── models.py       # SQLAlchemy ORM-модели
│   ├── alembic/        # Миграции Alembic
│   ├── repository/     # Слой доступа к данным
│   └── scripts/        # Утилиты (создание БД, загрузка данных)
├── elastic/
│   ├── service.py      # Elasticsearch-клиент
│   └── scripts/        # Утилиты (создание/удаление индекса, загрузка)
├── routes/             # Обработчики запросов
├── middleware/         
└── exceptions.py       # Доменные исключения

tests/
├── conftest.py         # Фикстуры
├── mocks/              # Моки и утилиты для тестов
└── tests/              # Тесты, зеркалирующие структуру src/
```
