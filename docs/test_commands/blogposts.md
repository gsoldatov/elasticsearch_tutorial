# Blogposts API Test Commands
```bash
BASE_URL="http://localhost:15001"
```

## Create
```bash
curl -s -X POST "$BASE_URL/blogposts/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-post-1",
    "title": "Введение в FastAPI",
    "text": "FastAPI — это современный веб-фреймворк для Python.",
    "tags": ["python", "fastapi", "web"],
    "updated_at": "2026-08-01T12:00:00+00:00"
  }' | python3 -m json.tool --no-ensure-ascii
```


## Get by ID
```bash
curl -s "$BASE_URL/blogposts/1" | python3 -m json.tool --no-ensure-ascii
```


## Update
```bash
curl -s -X PATCH "$BASE_URL/blogposts/1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Обновлённый заголовок",
    "text": "Обновлённый текст поста.",
    "tags": ["python", "updated"],
    "updated_at": "2026-08-01T12:00:00+00:00"
  }' | python3 -m json.tool --no-ensure-ascii
```


## Delete
```bash
curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/blogposts/1"
```


## Search
```bash
curl -s -G "$BASE_URL/blogposts/search" \
  --data-urlencode "q=python" \
  --data-urlencode "tags=fastapi,web" \
  --data-urlencode "min_time=2026-01-01T00:00:00+00:00" \
  --data-urlencode "max_time=2026-12-31T23:59:59+00:00" \
  --data-urlencode "p=1" \
  --data-urlencode "per_page=5" \
  | python3 -m json.tool --no-ensure-ascii
```


## Search Tags
```bash
curl -s -G "$BASE_URL/blogposts/search_tags" \
  --data-urlencode "q=py" \
  | python3 -m json.tool --no-ensure-ascii
```


## Vector Search
```bash
curl -s -G "$BASE_URL/blogposts/vector_search" \
  --data-urlencode "q=введение в Python" \
  | python3 -m json.tool --no-ensure-ascii
```


## Hybrid Search
```bash
curl -s -G "$BASE_URL/blogposts/hybrid_search" \
  --data-urlencode "q=Elasticsearch поиск" \
  | python3 -m json.tool --no-ensure-ascii
```