# eWorks Products sync

Sync eWorks Manager **Items** (type `Products` only) into the local `products` table for use in the estimate wizard product dropdown.

## Environment

Uses the same credentials as the Customer API:

```env
EWORKS_BASE_URL=https://your-eworks-host
EWORKS_API_KEY=your-api-key
```

`EWORKS_API_ENABLED` is **not** required for product sync (only for Customer lookup on link open).

## Sync products

```bash
curl -X POST \
  -H "X-Dashboard-Password: YOUR_DASHBOARD_PASSWORD" \
  http://localhost:8000/api/v1/integrations/eworks/products/sync
```

Response:

```json
{
  "success": true,
  "data": {
    "message": "eWorks products synced successfully",
    "summary": {
      "total_fetched": 1391,
      "inserted": 120,
      "updated": 1271,
      "skipped": 0
    }
  },
  "meta": {}
}
```

The sync paginates `GET {EWORKS_BASE_URL}/Item?page=N` until all pages are fetched, filters to `item_type.item_type == "Products"`, and upserts by `eworks_item_id`.

## List products (wizard / API)

```bash
curl "http://localhost:8000/api/v1/products?search=Plant&per_page=100"
curl "http://localhost:8000/api/v1/products?has_scope_of_work=true"
curl "http://localhost:8000/api/v1/products/1"
```

## Database migration

After deploy:

```bash
alembic upgrade head
```

Adds migration `010_products`.

## Field mapping

| eWorks | Local |
|--------|-------|
| `id` | `eworks_item_id` |
| `item_name` | `product_name` |
| `item_code` | `product_code` |
| `item_description` | `scope_of_work` |
| `price` | `selling_price` |
| `cost_price` | `cost_price` |
| `item_margin` | `margin` |

Only items with `item_type.item_type == "Products"` are stored.

## Estimate wizard

Each work block accordion header shows a searchable product dropdown. Selecting a product auto-fills **Scope of Works** from `scope_of_work` (editable). Product metadata and final scope are saved in `step2_snapshot.works[]`. Product pricing fields are stored for reference only and do **not** affect quote totals in this release.
