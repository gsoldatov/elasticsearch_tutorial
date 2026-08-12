# Sales API Test Commands
```bash
BASE_URL="http://localhost:15001"
```


## By Month and Region
```bash
curl -s -G "$BASE_URL/sales/by_month_and_region" \
  --data-urlencode "min_date=2024-01-01" \
  --data-urlencode "max_date=2024-12-31" \
  --data-urlencode "region=Russia,Germany" \
  | python3 -m json.tool --no-ensure-ascii
```


## Top Products
```bash
curl -s -G "$BASE_URL/sales/top_products" \
  --data-urlencode "n=5" \
  --data-urlencode "region=Russia" \
  | python3 -m json.tool --no-ensure-ascii
```


## Units Sold Groups
```bash
curl -s -G "$BASE_URL/sales/units_sold_groups" \
  --data-urlencode "min_date=2024-01-01" \
  --data-urlencode "max_date=2024-12-31" \
  | python3 -m json.tool --no-ensure-ascii
```
