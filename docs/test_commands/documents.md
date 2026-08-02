# API Test Commands
```bash
BASE_URL="http://localhost:15001"
```


## Search
```bash
## 200
curl -s -G "$BASE_URL/documents/search" --data-urlencode "q=уголовного кодекса" | python3 -m json.tool --no-ensure-ascii

## 404
curl -s -G "$BASE_URL/documents/search" --data-urlencode "q=уги буги" | python3 -m json.tool --no-ensure-ascii

# Search with verbose output — shows HTTP status, headers, and response body
curl -v -G "$BASE_URL/documents/search" --data-urlencode "q=гражданский кодекс"
```


## Delete
```bash
# 204 (on first call)
curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/documents/1"

# 404
curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/documents/999999"
```
