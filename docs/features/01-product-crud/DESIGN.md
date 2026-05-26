# Feature Design: CRUD Product

> Output từ skill `ba-spec` PHA 2. How (technical design).

## Architecture overview

```
┌───────────────────────────────────────────────────────────────┐
│  Catalog Manager (browser)                                    │
└──────────────────────────┬────────────────────────────────────┘
                           │ HTTPS
        ┌──────────────────▼──────────────────┐
        │  Next.js (admin)                     │
        │   /admin/products            (list)  │
        │   /admin/products/new        (create)│
        │   /admin/products/[id]       (edit)  │
        │                                      │
        │  lib/api/products.ts                 │
        │  lib/hooks/use-products.ts (RQ)      │
        │  lib/schemas/product.ts (zod)        │
        └──────────────────┬───────────────────┘
                           │ axios + Bearer JWT
        ┌──────────────────▼──────────────────┐
        │  Django: /api/v1/catalog/products/  │
        │   ViewSet (thin)                     │
        │      ↓                               │
        │   Service: product_create/update/    │
        │       delete/restore                 │
        │   Selector: list_products,           │
        │       get_product                    │
        │      ↓                               │
        │   Model: Product (extends BaseModel) │
        │      ↓                               │
        │   AuditLog (via service)             │
        └──────────────────┬───────────────────┘
                           │
                   ┌───────▼────────┐
                   │  Postgres 16   │
                   │  catalog_products│
                   │  core_audit_logs│
                   └────────────────┘
```

## Component breakdown

### Backend (Django)

**New app**: `apps/catalog`

**New files**:
- `apps/catalog/__init__.py`
- `apps/catalog/apps.py` — `CatalogConfig`
- `apps/catalog/models.py` — `Product` (extends `BaseModel`)
- `apps/catalog/admin.py` — `ProductAdmin` (Django Admin)
- `apps/catalog/exceptions.py` — `ProductError`, `DuplicateSlugError`, `DuplicateSkuRootError`
- `apps/catalog/services/__init__.py`
- `apps/catalog/services/products.py` — `product_create`, `product_update`, `product_soft_delete`, `product_restore`
- `apps/catalog/selectors/__init__.py`
- `apps/catalog/selectors/products.py` — `list_products`, `get_product`
- `apps/catalog/serializers/__init__.py`
- `apps/catalog/serializers/products.py` — `ProductInputSerializer`, `ProductOutputSerializer`, `ProductListItemSerializer`
- `apps/catalog/views/__init__.py`
- `apps/catalog/views/products.py` — `ProductViewSet`
- `apps/catalog/filters.py` — `ProductFilter` (django-filter)
- `apps/catalog/urls.py` — DRF router
- `apps/catalog/migrations/0001_initial.py`
- `apps/catalog/tests/__init__.py`
- `apps/catalog/tests/factories.py` — `ProductFactory`
- `apps/catalog/tests/conftest.py`
- `apps/catalog/tests/test_services.py`
- `apps/catalog/tests/test_selectors.py`
- `apps/catalog/tests/test_viewset.py`
- `apps/catalog/tests/test_models.py`

**Modified files**:
- `config/settings/base.py` — thêm `"apps.catalog"` vào `LOCAL_APPS`
- `config/urls.py` — uncomment `path("catalog/", include("apps.catalog.urls"))`

### Frontend (Next.js)

**New files**:
- `src/app/(admin)/layout.tsx` — admin shell (top bar tạm, để feature accounts làm sau)
- `src/app/(admin)/products/page.tsx` — server component, fetch initial data + render list client
- `src/app/(admin)/products/_components/products-list-client.tsx` — TanStack Table client
- `src/app/(admin)/products/_components/columns.tsx` — table column defs
- `src/app/(admin)/products/_components/products-toolbar.tsx` — search + filter + "New" button
- `src/app/(admin)/products/new/page.tsx` — create form page
- `src/app/(admin)/products/[id]/page.tsx` — edit form page
- `src/app/(admin)/products/_components/product-form.tsx` — RHF form, shared create+edit
- `src/app/(admin)/products/_components/delete-confirm-dialog.tsx`
- `src/lib/api/products.ts` — `listProducts`, `getProduct`, `createProduct`, `updateProduct`, `deleteProduct`, `restoreProduct`
- `src/lib/hooks/use-products.ts` — TanStack Query hooks
- `src/lib/schemas/product.ts` — zod schemas (shared FE validate + type inference)
- `src/lib/types/product.ts` — TS interface mirror BE serializer
- `src/components/ui/input.tsx` — shadcn add
- `src/components/ui/label.tsx` — shadcn add
- `src/components/ui/textarea.tsx` — shadcn add
- `src/components/ui/select.tsx` — shadcn add
- `src/components/ui/badge.tsx` — shadcn add
- `src/components/ui/dialog.tsx` — shadcn add
- `src/components/ui/table.tsx` — shadcn add

**Note**: shadcn components add qua `npx shadcn@latest add <name>` — KHÔNG sửa tay sau đó. Đây không phải dep mới cần user confirm.

## Data Flow

```
1. User action (click "Save" on form)
        ↓
2. RHF validate qua zodResolver (FE-side)
        ↓
3. useMutation.mutate(data)
        ↓ axios POST /api/v1/catalog/products/
4. Axios interceptor attach Bearer token
        ↓
5. Django ProductViewSet.create()
        ↓ ProductInputSerializer validate (BE-side)
6. services.products.product_create(actor, **data)
        ↓ @transaction.atomic
7. Validate business rules (sku_root format, unique)
        ↓
8. Product.objects.create(...)
        ↓
9. audit_log_create(action='create', entity=product, actor=actor, changes={...})
        ↓
10. Return Product instance
        ↓
11. ProductOutputSerializer serialize → JSON
        ↓ 201 Created
12. FE: TanStack Query invalidate ['products'] → list refetch
        ↓
13. toast.success + router.push('/admin/products')
```

## State Management

- **Server state**: TanStack Query
  - Key factory:
    ```ts
    export const productKeys = {
      all: ['products'] as const,
      lists: () => [...productKeys.all, 'list'] as const,
      list: (filters: ProductListParams) => [...productKeys.lists(), filters] as const,
      details: () => [...productKeys.all, 'detail'] as const,
      detail: (id: string) => [...productKeys.details(), id] as const,
    };
    ```
- **Local state**: useState (form ko cần persisted, RHF tự quản)
- **URL state**: `useSearchParams` cho `?page=N&search=Q&status=S&show_archived=true` — preserve khi reload
- **Persisted client**: KHÔNG dùng IndexedDB (Product không cần offline; POS sau này mới cần)

## API Contract

### List products
```
GET /api/v1/catalog/products/?page=1&page_size=20&search=dragon&status=active&show_archived=false&ordering=-updated_at
Auth: Bearer

Response 200:
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/catalog/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Dragon Figure",
      "slug": "dragon-figure",
      "sku_root": "DRAGON",
      "status": "active",
      "brand": "ABC",
      "tags": ["figure", "dragon"],
      "updated_at": "2026-05-26T10:30:00+07:00",
      "deleted_at": null
    }
  ]
}
```

### Get product detail
```
GET /api/v1/catalog/products/{id}/
Auth: Bearer

Response 200: Full ProductOutputSerializer
{
  "id": "uuid",
  "name": "Dragon Figure",
  "slug": "dragon-figure",
  "sku_root": "DRAGON",
  "status": "active",
  "short_description": "...",
  "long_description": "...",
  "brand": "ABC",
  "tags": ["figure", "dragon"],
  "attributes": { "scale": "1:10", "estimated_weight_g": 120 },
  "created_at": "2026-05-26T10:00:00+07:00",
  "updated_at": "2026-05-26T10:30:00+07:00",
  "deleted_at": null,
  "created_by": { "id": 1, "username": "alice" },
  "updated_by": { "id": 1, "username": "alice" }
}

Errors:
- 404 NOT_FOUND nếu product không tồn tại hoặc deleted (mặc định selector exclude deleted)
```

### Create product
```
POST /api/v1/catalog/products/
Auth: Bearer
Body:
{
  "name": "Dragon Figure",
  "slug": "dragon-figure",        // optional, BE auto-generate nếu trống
  "sku_root": "DRAGON",
  "status": "draft",              // default "draft"
  "short_description": "",        // optional
  "long_description": "",         // optional
  "brand": "",                    // optional
  "tags": [],                     // optional, default []
  "attributes": {}                // optional, default {}
}

Response 201: ProductOutputSerializer

Errors:
- 400 VALIDATION_ERROR:
  {
    "name": ["Trường này là bắt buộc"],
    "sku_root": ["Phải 3-8 ký tự hoa số"],
    "slug": ["Slug đã tồn tại"]
  }
- 401 nếu chưa auth
```

### Update product (partial)
```
PATCH /api/v1/catalog/products/{id}/
Auth: Bearer
Body: chỉ field cần update
{
  "name": "Dragon Figure v2"
}

Response 200: ProductOutputSerializer
Errors: 400, 401, 404
```

### Delete (soft) product
```
DELETE /api/v1/catalog/products/{id}/
Auth: Bearer

Response 204 No Content
Errors: 401, 404
```

### Restore product
```
POST /api/v1/catalog/products/{id}/restore/
Auth: Bearer

Response 200: ProductOutputSerializer (deleted_at = null)
Errors: 401, 404 (chỉ accept product đang ở trạng thái deleted)
```

## Database changes

### New table `catalog_products`
```sql
CREATE TABLE catalog_products (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name varchar(200) NOT NULL,
    slug varchar(220) NOT NULL,
    sku_root varchar(8) NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'draft',
    short_description text NOT NULL DEFAULT '',
    long_description text NOT NULL DEFAULT '',
    brand varchar(100) NOT NULL DEFAULT '',
    tags varchar(64)[] NOT NULL DEFAULT '{}',
    attributes jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    created_by_id integer REFERENCES auth_user(id) ON DELETE SET NULL,
    updated_by_id integer REFERENCES auth_user(id) ON DELETE SET NULL,
    deleted_by_id integer REFERENCES auth_user(id) ON DELETE SET NULL,

    CONSTRAINT catalog_products_status_check
        CHECK (status IN ('draft', 'active', 'archived'))
);

-- Unique constraints (case-insensitive, chỉ áp dụng row chưa soft-deleted)
CREATE UNIQUE INDEX catalog_products_slug_lower_alive_idx
    ON catalog_products (LOWER(slug))
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX catalog_products_sku_root_lower_alive_idx
    ON catalog_products (LOWER(sku_root))
    WHERE deleted_at IS NULL;

-- Search indexes
CREATE INDEX catalog_products_name_trgm_idx
    ON catalog_products USING gin (name gin_trgm_ops);

CREATE INDEX catalog_products_sku_root_trgm_idx
    ON catalog_products USING gin (sku_root gin_trgm_ops);

CREATE INDEX catalog_products_attributes_gin_idx
    ON catalog_products USING gin (attributes);

CREATE INDEX catalog_products_tags_gin_idx
    ON catalog_products USING gin (tags);

CREATE INDEX catalog_products_updated_at_idx
    ON catalog_products (updated_at DESC);

CREATE INDEX catalog_products_status_idx
    ON catalog_products (status) WHERE deleted_at IS NULL;
```

### Migration plan
1. Create migration `apps/catalog/migrations/0001_initial.py` qua `makemigrations`
2. Add raw SQL operations cho partial unique index + GIN trigram indexes (Django ORM không expose `Lower()` trong UniqueConstraint cho PostgreSQL partial qua một số version cũ — verify thực tế khi run)
3. Apply migration: `python manage.py migrate catalog`
4. Verify: psql `\d catalog_products`

**Extensions** (đã enable qua `backend/scripts/postgres-init.sql` khi docker up): `pg_trgm`, `unaccent`, `btree_gin`, `uuid-ossp`.

## Technical Decisions

### Decision 1: Service layer pattern (HackSoft)
- **Options considered**: A) Fat ViewSet với business logic inline; B) Fat model với manager methods; C) Service layer
- **Chose**: C (service layer trong `services/products.py`)
- **Because**: tech-stack.md đã chốt; reuse logic ở Celery / management commands; test không cần HTTP
- **Trade-off**: thêm 1 layer, dev quen "thin model + thin view" cần adapt

### Decision 2: Soft delete via `deleted_at` (không phải boolean `is_deleted`)
- **Options considered**: A) Boolean `is_deleted` + nullable `deleted_at`; B) Chỉ `deleted_at` (NULL = alive)
- **Chose**: B
- **Because**: 1 nguồn truth, partial unique index dùng `WHERE deleted_at IS NULL` clean, đã có sẵn trong `apps.core.SoftDeleteModel`
- **Trade-off**: query phải check `IS NULL`, đã abstract qua `SoftDeleteManager.get_queryset()`

### Decision 3: Partial unique index cho slug/sku_root
- **Options considered**: A) Plain unique constraint (block soft-delete + tạo lại); B) Partial unique `WHERE deleted_at IS NULL`
- **Chose**: B
- **Because**: cho phép tạo lại Product với slug giống sau khi xoá. Postgres native feature, không cần app logic.
- **Trade-off**: ORM ít direct support, phải dùng `Index(Lower('slug'), condition=...)` hoặc raw SQL trong migration.

### Decision 4: PATCH (partial) vs PUT (full replace)
- **Options considered**: A) Chỉ PATCH; B) Chỉ PUT; C) Cả 2
- **Chose**: A (chỉ PATCH; tắt PUT bằng `http_method_names`)
- **Because**: FE chỉ cần gửi field thay đổi, giảm conflict concurrent edit, giảm payload
- **Trade-off**: client không thể "reset" object về default; chấp nhận

### Decision 5: separate Input/Output serializer
- **Options considered**: A) 1 serializer dùng cả input + output; B) Tách 2
- **Chose**: B
- **Because**: HackSoft pattern; tránh write-only fields lộ ra output, output có thể nested user info, input chỉ field user nhập
- **Trade-off**: 2x maintenance khi schema đổi — accept

### Decision 6: pagination — PageNumberPagination default DRF
- **Already configured** trong `config/settings/base.py` REST_FRAMEWORK, page_size=20
- **Because**: đơn giản nhất, đủ cho catalog < 10k Product. Cursor pagination defer khi scale.

### Decision 7: ArrayField cho `tags` thay vì m2m bảng `tags`
- **Options considered**: A) m2m `tags` table; B) `ArrayField(varchar)`
- **Chose**: B
- **Because**: tag không có entity riêng (chỉ string), GIN index hỗ trợ filter `?tags__contains=["dragon"]` đủ nhanh, đơn giản hơn 1 bảng + 1 m2m
- **Trade-off**: không có tag canonical (vd "Dragon" vs "dragon" coi như 2 tag khác). Mitigation: lowercase + trim ở serializer trước khi lưu.

### Decision 8: `restore` là @action thay vì PUT trên field
- **Options considered**: A) POST `/restore/` action; B) PATCH với `{ deleted_at: null }`
- **Chose**: A (custom @action)
- **Because**: explicit ý định, audit log dễ phân biệt action=restore vs action=update, query selector dễ filter chỉ restore-able
- **Trade-off**: thêm 1 endpoint, chấp nhận

## Security considerations

- **AuthN**: JWT Bearer (`rest_framework_simplejwt.authentication.JWTAuthentication` đã default trong base settings)
- **AuthZ**: `IsAuthenticated` ở viewset (TODO: lock down theo role khi `accounts` app có). Comment TODO trong ViewSet.
- **IDOR**: Product không có owner field → 1 user authenticated thấy mọi Product (đúng business: catalog dùng chung). Sau này nếu có multi-tenant cần thêm `team_id` filter.
- **Input validation**: zod (FE) + DRF serializer + Django field validators + DB CHECK constraint (defense in depth)
- **Rate limit**: chưa cần (internal tool 6-10 user); defer
- **SQL injection**: ORM-only, không raw SQL với user input (riêng index raw SQL trong migration không nhận input)
- **XSS trên `long_description` markdown**: FE render markdown phải sanitize. Lần này UI chỉ là textarea raw, không render markdown → defer khi có view detail nice.

## Performance considerations

- **Expected load**: ~5 concurrent CM, ~50 list requests/giờ. Không phải hot path.
- **Query optimization**:
  - List: `.only(...)` các field cần cho list (loại `long_description`, `attributes` nặng) → ProductListItemSerializer fields hẹp
  - Detail: `.select_related('created_by', 'updated_by')` để serialize nested user 1 query
- **Caching**: chưa cần
- **Async**: tất cả endpoint < 500ms target, không qua Celery

## Test strategy

| Layer | Tool | Coverage target |
|---|---|---|
| Model + Manager | pytest + factory_boy | 100% |
| Service (business logic + validate) | pytest | 100% — đây là core |
| Selector | pytest | 90% |
| Serializer | pytest (parametrize) | 80% |
| ViewSet integration | pytest + APIClient | 80% — happy + error paths |
| FE schema (zod) | Vitest | 100% — pure functions |
| FE hooks | Vitest + MSW | happy path |
| E2E | Playwright | 1 happy path: login → create → edit → delete |

**Cross-cutting tests**:
- Race condition: 2 concurrent POST cùng sku_root → 1 trả 201, 1 trả 400 (test với threading)
- Soft delete + tạo lại slug: pass
- Audit log entry sau mỗi mutation: assert AuditLog.objects.filter(...).exists()

## Rollout plan

1. Apply migration trên dev DB (Docker postgres) → smoke `python manage.py shell` create 1 Product
2. Curl `/api/v1/catalog/products/` đăng nhập user test → 200 OK
3. FE `npm run dev` → manual flow create → list → edit → delete
4. Run full test suite: `pytest apps/catalog --cov` + `npm run typecheck` + `npm test`
5. Commit + push branch
6. (Future) Deploy staging → UAT → prod

## Rollback plan

Nếu issue sau merge:
1. Revert commit feature → migration vẫn còn nhưng table có thể trống
2. Reverse migration: `python manage.py migrate catalog zero` → drop table
3. Re-deploy

Vì là feature đầu tiên + chưa có data prod → rollback risk gần như 0.

---

*Created by skill: `ba-spec` | Date: 2026-05-26*
