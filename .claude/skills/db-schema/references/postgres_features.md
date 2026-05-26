# PostgreSQL Features dùng trong dự án

## 1. JSONB cho dynamic attributes

### Khi nào dùng

Variant có 5 trục chính (material, color, size, layer_resolution, infill) là column riêng. Các attribute hiếm hơn (finish, food_safe, durability_rating) → JSONB.

```sql
-- Schema
ALTER TABLE skus_variants ADD COLUMN attributes jsonb NOT NULL DEFAULT '{}';
CREATE INDEX idx_variant_attributes_gin ON skus_variants USING GIN (attributes jsonb_path_ops);
```

### Query patterns

```sql
-- Containment (most performant với jsonb_path_ops)
SELECT * FROM skus_variants WHERE attributes @> '{"finish": "matte"}';

-- Multiple containment
SELECT * FROM skus_variants WHERE attributes @> '{"finish": "matte", "food_safe": true}';

-- Path exists
SELECT * FROM skus_variants WHERE attributes ? 'durability_rating';

-- Path value
SELECT * FROM skus_variants WHERE attributes->>'finish' = 'matte';

-- Numeric comparison (cần cast)
SELECT * FROM skus_variants WHERE (attributes->>'durability_rating')::int >= 8;
```

### Django ORM

```python
# Containment
Variant.objects.filter(attributes__contains={'finish': 'matte'})

# Has key
Variant.objects.filter(attributes__has_key='durability_rating')

# Get value
Variant.objects.filter(attributes__finish='matte')

# Update single key (PostgreSQL JSON path operations)
from django.db.models import F
from django.contrib.postgres.fields.jsonb import KeyTransform

Variant.objects.update(
    attributes=models.functions.JSONObject(
        finish='glossy',
        food_safe=KeyTransform('food_safe', 'attributes'),
    )
)
```

### jsonb_set, jsonb_path_query (advanced)

```sql
-- Update 1 key
UPDATE skus_variants 
SET attributes = jsonb_set(attributes, '{finish}', '"glossy"')
WHERE id = '...';

-- Update nested
UPDATE skus_variants 
SET attributes = jsonb_set(attributes, '{dimensions,weight}', '120')
WHERE id = '...';
```

## 2. ltree cho Category tree

ltree cho phép query cây hierarchy hiệu quả hơn adjacency list.

### Setup

```sql
CREATE EXTENSION ltree;

ALTER TABLE catalog_categories ADD COLUMN path ltree NOT NULL;
CREATE INDEX idx_category_path_gist ON catalog_categories USING GIST (path);
```

Path format: `gadget.phone_accessory.case` (dấu chấm phân cách level).

### Queries

```sql
-- Tất cả descendants của 'gadget'
SELECT * FROM catalog_categories WHERE path <@ 'gadget';

-- Tất cả ancestors của 'gadget.phone_accessory.case'
SELECT * FROM catalog_categories WHERE 'gadget.phone_accessory.case' <@ path;

-- Direct children only
SELECT * FROM catalog_categories WHERE path ~ 'gadget.*{1}';

-- Depth = 2 (gadget.X)
SELECT * FROM catalog_categories WHERE nlevel(path) = 2 AND path ~ 'gadget.*';

-- Products thuộc 1 category tree
SELECT p.* FROM catalog_products p
JOIN catalog_product_categories pc ON pc.product_id = p.id
JOIN catalog_categories c ON c.id = pc.category_id
WHERE c.path <@ 'gadget.phone_accessory';
```

### Django (django-ltree)

```python
from django_ltree.fields import PathField
from django_ltree.models import TreeModel

class Category(TreeModel):
    path = PathField()
    name = models.CharField(max_length=120)

# Usage
gadget = Category.objects.get(path='gadget')
descendants = Category.objects.filter(path__descendant_of='gadget')
```

## 3. Trigram fuzzy search

Tìm sản phẩm với typo / partial match.

```sql
CREATE EXTENSION pg_trgm;

CREATE INDEX idx_product_name_trgm ON catalog_products USING GIN (name gin_trgm_ops);

-- Similarity search
SELECT name, similarity(name, 'dragon figue') AS sim
FROM catalog_products
WHERE name % 'dragon figue'
ORDER BY sim DESC LIMIT 10;

-- ILIKE benefits từ trigram index
SELECT * FROM catalog_products WHERE name ILIKE '%dragon%';
```

### Django

```python
from django.contrib.postgres.search import TrigramSimilarity

Product.objects.annotate(
    sim=TrigramSimilarity('name', 'dragon figue')
).filter(sim__gt=0.3).order_by('-sim')
```

## 4. Unaccent cho Vietnamese search

VN dùng dấu — user gõ "ao thun" phải match "Áo thun".

```sql
CREATE EXTENSION unaccent;

-- Index trên unaccent (cần IMMUTABLE wrapper)
CREATE OR REPLACE FUNCTION immutable_unaccent(text) RETURNS text AS $$
  SELECT unaccent('unaccent', $1);
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;

CREATE INDEX idx_product_name_unaccent ON catalog_products 
USING GIN (immutable_unaccent(name) gin_trgm_ops);

-- Query
SELECT * FROM catalog_products 
WHERE immutable_unaccent(name) ILIKE immutable_unaccent('%ao thun%');
```

### Django combo

```python
from django.contrib.postgres.search import (
    SearchVector, SearchQuery, SearchRank
)
from django.db.models.functions import Concat

# Full-text search với Vietnamese
Product.objects.annotate(
    search=SearchVector('name', 'short_description', 'long_description', config='simple')
).filter(search=SearchQuery('áo thun', config='simple'))
```

## 5. Partial index

Index chỉ subset rows → nhỏ hơn, nhanh hơn.

```sql
-- Chỉ index variants chưa bị soft-delete
CREATE INDEX idx_variant_active ON skus_variants (status, product_id)
WHERE deleted_at IS NULL;

-- Chỉ index listings đang sync error (để retry job tìm nhanh)
CREATE INDEX idx_listing_error ON channels_channel_listings (channel, updated_at)
WHERE status = 'error';
```

### Django

```python
class Meta:
    indexes = [
        models.Index(
            fields=['status', 'product'],
            name='idx_variant_active',
            condition=models.Q(deleted_at__isnull=True),
        ),
    ]
```

## 6. Materialized view (cached aggregation)

Cho dashboard không cần real-time, refresh hourly.

```sql
CREATE MATERIALIZED VIEW mv_product_sales_summary AS
SELECT 
    p.id AS product_id,
    p.name,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(oi.quantity * oi.unit_price) AS total_revenue,
    MAX(o.created_at) AS last_sold_at
FROM catalog_products p
LEFT JOIN orders_order_items oi ON oi.product_id = p.id
LEFT JOIN orders_unified_orders o ON o.id = oi.order_id
WHERE o.created_at > NOW() - INTERVAL '90 days'
GROUP BY p.id, p.name;

CREATE UNIQUE INDEX ON mv_product_sales_summary (product_id);

-- Refresh (concurrently giữ readable)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_sales_summary;
```

Schedule refresh qua Celery beat:

```python
CELERY_BEAT_SCHEDULE = {
    'refresh-product-sales-summary': {
        'task': 'apps.analytics.tasks.refresh_product_sales_summary',
        'schedule': crontab(minute=0, hour='*'),
    },
}
```

## 7. Generated column (Postgres 12+)

Compute từ column khác, tự sync.

```sql
ALTER TABLE skus_variants ADD COLUMN gross_margin numeric(12,2) 
GENERATED ALWAYS AS (base_price - cost_price) STORED;

ALTER TABLE skus_variants ADD COLUMN margin_percent numeric(5,2)
GENERATED ALWAYS AS (
    CASE WHEN base_price > 0 THEN ((base_price - cost_price) / base_price * 100) ELSE 0 END
) STORED;
```

Django chưa native support, dùng `RunSQL` migration.

## 8. Row-level security (optional, multi-tenant)

Nếu sau này multi-tenant, RLS auto filter theo tenant_id:

```sql
ALTER TABLE catalog_products ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON catalog_products
USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Trong app, set tenant cho mỗi connection
SET app.current_tenant = 'tenant-uuid-here';
```

## 9. Lock-free deduplication (UPSERT)

```sql
-- ON CONFLICT cho idempotent insert
INSERT INTO channels_processed_events (source, external_event_id, payload, processed_at)
VALUES ('shopee', 'evt-123', '{}', NOW())
ON CONFLICT (source, external_event_id) DO NOTHING
RETURNING id;
```

### Django

```python
from django.db.models import Q
from django.db import IntegrityError

# Approach 1: get_or_create (2 queries)
event, created = ProcessedEvent.objects.get_or_create(
    source='shopee',
    external_event_id='evt-123',
    defaults={'payload': payload},
)

# Approach 2: raw UPSERT for performance
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        INSERT INTO channels_processed_events (source, external_event_id, payload, processed_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (source, external_event_id) DO NOTHING
        RETURNING id
    """, ['shopee', 'evt-123', json.dumps(payload)])
    row = cursor.fetchone()
    created = row is not None
```

## 10. Connection pooling

Production cần PgBouncer (transaction mode):

```ini
# pgbouncer.ini
[databases]
mydb = host=db.local port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

Django settings:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'localhost',  # PgBouncer
        'PORT': 6432,
        'NAME': 'mydb',
        'CONN_MAX_AGE': 0,  # MUST 0 for transaction pooling
        'DISABLE_SERVER_SIDE_CURSORS': True,
    }
}
```
