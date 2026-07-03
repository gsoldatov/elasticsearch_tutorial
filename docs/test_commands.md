# API Test Commands
Base URL: `http://localhost:15001`


## Search
```bash
## 200
curl -s -G "http://localhost:15001/search" --data-urlencode "q=уголовного кодекса" | python3 -m json.tool --no-ensure-ascii

## 404
curl -s -G "http://localhost:15001/search" --data-urlencode "q=уги буги" | python3 -m json.tool --no-ensure-ascii

# Search with verbose output — shows HTTP status, headers, and response body
curl -v -G "http://localhost:15001/search" --data-urlencode "q=гражданский кодекс"
```


## Delete
```bash
# 204 (on first call)
curl -s -o /dev/null -w "%{http_code}" -X DELETE "http://localhost:15001/documents/1"

# 404
curl -s -o /dev/null -w "%{http_code}" -X DELETE "http://localhost:15001/documents/999999"
```
