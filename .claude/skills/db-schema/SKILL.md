---
name: db-schema
description: Thiết kế database schema và Django models/migrations cho hệ thống quản lý SKU in 3D đa kênh. Use this skill whenever the user mentions "schema", "database", "ERD", "model", "migration", "table", "Django model", "thiết kế DB", "cấu trúc bảng", "quan hệ bảng", or asks about data modeling — even casually like "viết schema cho ...", "tạo bảng X", "model cho module Y". Also triggers for PostgreSQL-specific features (JSONB, ltree, GIN index, partial index, materialized view), data migration scripts, soft delete patterns, audit log design, and BOM/recipe-style relational structures.
---

# DB Schema Designer cho dự án 3D Printing PIM

Skill này thiết kế schema PostgreSQL và Django models cho dự án. Stack: **PostgreSQL 16 + Django 5 ORM**.

## Nguyên tắc thiết kế

### 1. ID strategy
- **UUID v4** cho PK của entity exposed qua API (products, variants, orders, design_files). Tránh enum sequential ID rò rỉ business info.
- **BigAutoField (bigint)** cho table chỉ internal (audit_log, processed_events, sync_jobs) — performance tốt hơn UUID cho high-volume insert.
- **`uuid_generate_v7()`** (extension) nếu muốn UUID time-ordered cho index locality.

### 2. JSONB cho attributes động

Thay vì EAV truyền thống, dùng JSONB:

```sql
CREATE TABLE variants (
    id uuid PRIMARY KEY,
    sku varchar(32) UNIQUE NOT NULL,
    attributes jsonb NOT NULL DEFAULT '{}',
    ...
);

-- GIN index cho query containment
CREATE INDEX idx_variant_attributes_gin ON variants USING GIN (attributes jsonb_path_ops);

-- Query example: tìm variants có material PLA + color red
SELECT * FROM variants WHERE attributes @> '{"material": "PLA", "color": "red"}';
```

**Khi nào promote JSONB key thành column riêng?** Khi:
- Query/filter trên key đó > 1000 lần/ngày
- Cần check constraint (vd `infill_percent BETWEEN 0 AND 100`)
- Cần index B-tree riêng (range queries)

### 3. Soft delete pattern

```python
class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)
    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    objects = SoftDeleteManager()       # default: alive only
    all_objects = models.Manager()       # for admin
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def hard_delete(self):
        super().delete()
```

### 4. Audited model

```python
class AuditedModel(models.Model):
    created_by = models.ForeignKey(
        'accounts.User', null=True, on_delete=models.SET_NULL,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        'accounts.User', null=True, on_delete=models.SET_NULL,
        related_name='+',
    )
    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```

### 5. PostgreSQL extensions cần enable

```sql
-- Trong migration đầu tiên
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- gen_random_uuid alternative
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- fuzzy search
CREATE EXTENSION IF NOT EXISTS "ltree";           -- category tree
CREATE EXTENSION IF NOT EXISTS "btree_gin";       -- composite GIN
CREATE EXTENSION IF NOT EXISTS "unaccent";        -- VN accent-insensitive search
```

Django migration:
```python
# apps/core/migrations/0001_extensions.py
from django.contrib.postgres.operations import (
    CryptoExtension, TrigramExtension, UnaccentExtension, BtreeGinExtension,
)
from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    operations = [
        CryptoExtension(),
        TrigramExtension(),
        UnaccentExtension(),
        BtreeGinExtension(),
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS "ltree";', reverse_sql='DROP EXTENSION IF EXISTS "ltree";'),
    ]
```

## Schema overview - 18 bảng cốt lõi

Xem `references/full_schema.md` cho từng bảng chi tiết. Tóm tắt:

### Auth & RBAC (3 bảng)
1. `accounts_user` (đã extend Django User)
2. `accounts_role` 
3. `accounts_permission`

### Catalog (4 bảng)
4. `catalog_categories` (ltree path)
5. `catalog_brands`
6. `catalog_products`
7. `catalog_attribute_definitions` (meta cho dynamic attributes)

### SKU/Variants (3 bảng)
8. `skus_variants`
9. `skus_sku_codes` (abbreviation library)
10. `media_assets` (polymorphic owner)

### Design files (1 bảng)
11. `design_files_files` (versioned)

### Manufacturing (4 bảng)
12. `materials_materials`
13. `manufacturing_boms`
14. `manufacturing_bom_lines`
15. `manufacturing_printers`

### POC / Ideas (2 bảng)
16. `poc_versions`
17. `ideas_product_ideas`

### Channels (3 bảng)
18. `channels_marketplace_credentials`
19. `channels_channel_listings`
20. `channels_processed_events` (idempotency)

### Operational (3 bảng)
21. `orders_unified_orders`
22. `core_audit_logs`
23. `core_dead_letters`

## Quan hệ chính (ERD text)

```
Category (ltree tree)
   ↓ 1:N
Product ─────────────────→ Brand
   ↓ 1:N (variants)
Variant ──────────────→ Material (PROTECT)
   ├─ design_file_id → DesignFile (PROTECT, null OK)
   ├─ 1:1 BOM
   │     └─ N:M Materials qua BomLine
   ├─ N:M Printer qua VariantCompatiblePrinter
   ├─ 1:N POCVersion (history)
   ├─ 1:N ChannelListing
   └─ 1:N MediaAsset

DesignFile (self-ref parent_file_id cho version tree)

User ←── many tables qua created_by/updated_by, AuditLog.actor

AuditLog (polymorphic entity reference)

ProcessedEvent (idempotency key cho webhook)
```

## Convention naming

| Item | Pattern | Example |
|---|---|---|
| Table | `{app}_{plural_lowercase}` | `skus_variants`, `catalog_products` |
| PK | `id` | always |
| FK column | `{singular}_id` | `product_id`, `material_id` |
| Boolean | `is_*`, `has_*`, `can_*` | `is_active`, `has_enclosure` |
| Date/time | `*_at` cho timestamp, `*_date` cho date | `created_at`, `purchase_date` |
| JSONB | `attributes`, `metadata`, `extra` | |
| Money | `numeric(12,2)` | `base_price`, `cost_price` |
| Decimal precision | document explicitly | `weight_g numeric(8,2)` |
| Index | `idx_{table}_{cols}` | `idx_variant_sku` |
| Unique constraint | `uq_{table}_{cols}` | `uq_variant_sku` |
| Check constraint | `chk_{table}_{rule}` | `chk_variant_base_price_nonneg` |

## Common queries cần support (test schema bằng các query này)

```sql
-- 1. Toàn bộ variants của product với SKU + giá + tồn kho
SELECT v.sku, v.base_price, COALESCE(SUM(ws.quantity), 0) as stock
FROM skus_variants v
LEFT JOIN warehouse_stocks ws ON ws.variant_id = v.id
WHERE v.product_id = $1 AND v.deleted_at IS NULL
GROUP BY v.id;

-- 2. Tổng PLA Red cần cho batch in 100 variants X
SELECT m.name, SUM(bl.quantity) * 100 AS needed
FROM manufacturing_bom_lines bl
JOIN materials_materials m ON m.id = bl.material_id
WHERE bl.bom_id = (
    SELECT id FROM manufacturing_boms WHERE variant_id = $1 AND is_active
)
AND m.subtype = 'pla' AND m.color = 'red'
GROUP BY m.id, m.name;

-- 3. Variants có thể in trên máy X
SELECT v.sku, vcp.estimated_minutes
FROM skus_variants v
JOIN variant_compatible_printers vcp ON vcp.variant_id = v.id
WHERE vcp.printer_id = $1
ORDER BY vcp.estimated_minutes;

-- 4. Sản phẩm thuộc category cha + cháu (ltree)
SELECT p.* FROM catalog_products p
JOIN catalog_product_categories pc ON pc.product_id = p.id
JOIN catalog_categories c ON c.id = pc.category_id
WHERE c.path <@ 'gadget.phone_accessory';

-- 5. Variants với license CC BY-NC đang active (cần migrate gấp)
SELECT v.sku, df.filename, df.license_type
FROM skus_variants v
JOIN design_files_files df ON df.id = v.design_file_id
WHERE v.status = 'active' AND df.license_type LIKE 'cc_by_nc%';

-- 6. Webhook đã process trong 24h (idempotency check)
SELECT external_event_id, processed_at
FROM channels_processed_events
WHERE source = 'shopee' AND processed_at > NOW() - INTERVAL '24 hours';
```

## Workflow khi user yêu cầu schema mới

1. **Xác định entity + boundary**: tách table như thế nào, gắn vào app nào.
2. **Identify relationships**: 1:1, 1:N, N:M (cần intermediate table?).
3. **Quyết định static vs dynamic attributes**: column riêng (filter nhiều) vs JSONB (linh hoạt).
4. **Constraints**:
   - Unique (đơn hoặc composite)
   - Check (range, format)
   - FK with on_delete strategy (PROTECT/CASCADE/SET_NULL)
5. **Indexes**: PK auto, FK auto trong Django, thêm index cho:
   - Field filter thường (status, deleted_at)
   - Field sort (created_at)
   - JSONB GIN
   - Trigram cho text search
6. **Migration plan**: 
   - Backward-compatible (deploy không downtime)
   - Backfill data trong RunPython
   - Index CONCURRENTLY cho production
7. **Soft delete + audit fields** mặc định.
8. **Validate qua sample queries** ở section "Common queries".

## Reference files

- `references/full_schema.md` — Toàn bộ 20+ bảng với SQL + Django models
- `references/migration_patterns.md` — Zero-downtime migration, backfill, index concurrently
- `references/postgres_features.md` — JSONB, ltree, GIN, partial index, materialized view

## Anti-patterns

❌ Lưu file binary trong DB → ✅ S3/MinIO, lưu key  
❌ Enum hardcode trong code, lưu int → ✅ Django TextChoices, lưu varchar  
❌ `null=True, blank=True` mọi field → ✅ chỉ khi thực sự nullable  
❌ FK `on_delete=CASCADE` mặc định → ✅ PROTECT cho master data, SET_NULL cho metadata  
❌ Lưu money là float → ✅ numeric(12,2) → DecimalField  
❌ Timezone-naive datetime → ✅ `USE_TZ = True` + DateTimeField(auto)  
❌ M:N qua `ManyToManyField` không through model → ✅ explicit through model nếu cần extra fields  
❌ Migration manual edit SQL → ✅ `makemigrations` + RunPython cho data migration  
❌ Drop column trực tiếp ở production → ✅ deprecate → backfill → drop (2-3 deploy steps)
