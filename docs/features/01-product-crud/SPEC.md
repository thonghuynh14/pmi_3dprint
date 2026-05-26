# Feature Spec: CRUD Product

> Output từ skill `ba-spec` PHA 2. What & Why của feature.

## Overview
CRUD cho entity Product (minimal scope) — foundational cho mọi feature catalog phía sau (Variant, ChannelListing, BOM, POC). Catalog Manager dùng Next.js admin UI; Super Admin có Django Admin auto-generated như backup.

## Stakeholders

- **Primary user**: Catalog Manager
- **Secondary**: Super Admin (Django Admin)
- **PM/Owner**: squad1@gosmartlog.com

## User Flow

```
1. Catalog Manager đăng nhập, vào /admin/products
2. Hệ thống hiển thị danh sách products (20/trang, sort updated_at desc)
   với search box, filter status, pagination control
3. CM click "New Product" → /admin/products/new
4. CM nhập name → slug tự generate (có thể edit), nhập sku_root (6 ký tự), status,
   short_description, long_description (markdown), brand (optional),
   tags (chip input), attributes (key-value JSONB editor)
5. CM click Save → POST /api/v1/catalog/products/
6. BE validate (slug+sku_root unique, format), create record, audit log → 201
7. FE invalidate TanStack Query cache → navigate back tới /admin/products
8. Toast success, product mới xuất hiện đầu list

9. CM click row → /admin/products/{id} (detail+edit form pre-filled)
10. CM edit → PATCH /api/v1/catalog/products/{id}/ → toast → list refresh
11. CM click Delete → confirm modal → DELETE /api/v1/catalog/products/{id}/
    (soft delete) → toast → list refresh
12. CM bật toggle "Show archived" → list hiển thị thêm record có deleted_at
```

## Acceptance Criteria (Given-When-Then)

### AC-1: Tạo product với data hợp lệ
```
Given Catalog Manager đăng nhập
And đang ở /admin/products/new
When CM nhập:
    name = "Dragon Figure"
    slug = "dragon-figure"
    sku_root = "DRAGON"
    status = "draft"
    short_description = "Mô hình rồng phong cách fantasy"
And click "Save"
Then hệ thống tạo Product với UUID mới
And response 201 trả về object với đầy đủ field bao gồm created_at, created_by
And user redirect về /admin/products
And toast "Đã tạo product 'Dragon Figure'" hiển thị
And AuditLog có entry: action=create, entity_type=product, actor=CM
```

### AC-2: Slug tự generate từ name khi tạo mới
```
Given CM ở /admin/products/new
When CM nhập name = "Dragon Figure v2"
And rời focus khỏi field name (blur event)
And field slug đang trống
Then field slug tự fill = "dragon-figure-v2"
And CM có thể edit lại slug nếu muốn
```

### AC-3: Validate slug + sku_root unique (case-insensitive)
```
Given DB đã có Product với slug = "dragon-figure" và sku_root = "DRAGON"
When CM submit form mới với slug = "Dragon-Figure" (case khác)
Or sku_root = "dragon" (case khác)
Then BE trả 400 với body:
    { "slug": ["Slug đã tồn tại"] } hoặc
    { "sku_root": ["Mã sku_root đã tồn tại"] }
And FE hiển thị error inline dưới field tương ứng
And không tạo record mới
```

### AC-4: Validate sku_root format
```
Given CM ở /admin/products/new
When CM nhập sku_root = "ab" (quá ngắn)
    or "DRAGON-FIRE" (có dấu gạch)
    or "Dragon" (chứa lowercase)
Then form hiển thị error inline trước khi submit (zod validation):
    "sku_root phải 3-8 ký tự, chỉ chữ in hoa và số (A-Z, 0-9)"
And Save button disabled hoặc submit bị block
```

### AC-5: Validate tags là array string
```
Given CM ở form create/edit
When CM nhập tags = ["figure", "dragon", "fantasy"]
And submit
Then BE accept và lưu vào ArrayField (PostgreSQL text[])
And response output trả về list các string giống vậy
```

### AC-6: List page filter + search + pagination
```
Given DB có 50 Product với status mix (30 active, 15 draft, 5 archived)
When CM vào /admin/products (mặc định không filter)
Then hiển thị 20 product đầu (sort updated_at desc)
And không bao gồm 5 archived (deleted_at IS NOT NULL)
And tổng count = 45

When CM gõ search "dragon" trong search box
Then list refresh với products có name HOẶC sku_root contains "dragon" (icontains)

When CM chọn filter status = "draft"
Then list chỉ còn product status=draft

When CM bật toggle "Show archived"
Then list bao gồm thêm record deleted_at IS NOT NULL
And mỗi archived row có badge "Archived"

When CM click page 2
Then load product thứ 21-40
And URL update ?page=2 (URL state preserved)
```

### AC-7: Edit (PATCH) chỉ field thay đổi
```
Given DB có Product P (name="A", description="B", status="draft")
And CM ở /admin/products/{id}
When CM đổi name → "A2" rồi Save
Then FE gửi PATCH với body chỉ chứa { name: "A2" } (RHF dirty fields only)
And BE update name, description giữ nguyên "B"
And AuditLog có entry action=update với diff {name: ["A", "A2"]}
And response trả về object mới với updated_at thay đổi
```

### AC-8: Soft delete + restore
```
Given Product P (name="Dragon", deleted_at=null)
When CM click Delete trên row của P
And confirm modal hiện ra với text "Xác nhận xoá 'Dragon'?"
And CM click "Xoá"
Then BE thực hiện soft delete: set P.deleted_at = now()
And response 204 No Content
And FE remove row khỏi list (TanStack Query invalidate)
And toast "Đã xoá 'Dragon'" có nút "Hoàn tác" trong 5s
And AuditLog có entry action=delete

When CM bật "Show archived" và click "Restore" trên row P
Then BE set P.deleted_at = null
And toast "Đã khôi phục 'Dragon'"
And AuditLog có entry action=restore
```

### AC-9: Permission — non-authenticated reject
```
Given user chưa đăng nhập (no JWT)
When request GET /api/v1/catalog/products/
Then response 401 Unauthorized

When request POST /api/v1/catalog/products/ với body hợp lệ
Then response 401 Unauthorized
```

### AC-10: API performance — list endpoint < 500ms p95
```
Given DB seed 1000 Product
And user đã đăng nhập
When 100 concurrent requests GET /api/v1/catalog/products/?page=1
Then 95% trong số đó response trong < 500ms
And không có 5xx error
```

## Edge Cases

- [x] **Empty state** (0 products): hiển thị illustration + CTA "Tạo product đầu tiên" → /admin/products/new
- [x] **Concurrent edit** (2 CM cùng PATCH 1 product): áp dụng last-write-wins, KHÔNG dùng optimistic locking (defer). Mitigation: PATCH chỉ gửi dirty fields → giảm conflict.
- [x] **Validation error trong nhiều field**: BE trả body { field1: [...], field2: [...] }, FE hiển thị từng field inline.
- [x] **Network failure mid-create**: TanStack Query mutation retry 1 lần; nếu vẫn fail → toast error + giữ form data (không clear).
- [x] **Tags chứa tiếng Việt có dấu**: hỗ trợ UTF-8 (PostgreSQL text[] mặc định). Lowercase trước khi lưu để dedup.
- [x] **Slug tự generate cho name có dấu**: dùng python-slugify với option remove unicode → "Mô hình rồng" → "mo-hinh-rong"
- [x] **sku_root collision với case khác** (xem AC-3): unique constraint với `LOWER(sku_root)` qua `UniqueConstraint(Lower('sku_root'))` của Django 5.
- [x] **Soft delete + tạo lại slug giống**: cho phép (slug unique chỉ trên `deleted_at IS NULL` qua partial unique index).
- [x] **Brand là string trống vs null**: form gửi "" → BE normalize thành null.
- [x] **Attributes JSONB key có dấu space hoặc đặc biệt**: validate ở serializer — chỉ cho ASCII alphanumeric + underscore + hyphen.
- [x] **Permission denied UI**: nếu user không phải Catalog Manager / Super Admin (sau khi có RBAC) → 403, FE hiển thị "Bạn không có quyền".

## Business Rules Applied

- **BR-009 (Audit log)**: mọi create/update/delete/restore tạo AuditLog entry với actor + diff + timestamp.
- **Tham chiếu BR-002** (SKU format): KHÔNG áp dụng cho `sku_root` (BR-002 là cho variant SKU). Riêng `sku_root` validate `^[A-Z0-9]{3,8}$` tách biệt.
- (Future) **BR-003** (license commercial check): KHÔNG áp dụng lần này vì chưa có design_files.

## Permissions

| Role | Can do |
|---|---|
| Super Admin | Tất cả (kể cả hard delete qua Django Admin) |
| Catalog Manager | List, Detail, Create, Update, Soft delete, Restore |
| Production Manager | List, Detail (read-only) |
| Channel Operator | List, Detail (read-only) |
| Designer | List, Detail (read-only) |
| Cashier | KHÔNG truy cập (POS scan thẳng variant) |
| Anonymous | 401 |

**Lần này (chưa có RBAC app)**: dùng `IsAuthenticated` cho mọi method. Lock down chi tiết khi feature `accounts/RBAC` triển khai. Comment TODO trong viewset.

## Out of Scope

Explicitly NOT in this feature:
- **Category m2m** — feature riêng `02-product-category` sau
- **Media upload** (hình sản phẩm 8 góc) — feature `03-product-media`
- **SEO override per channel** — feature Phase 2
- **Bulk import CSV/XLSX** — feature `04-product-bulk-import`
- **Lifecycle stage** (idea/concept/prototype/...) — gộp vào feature `Idea pipeline`
- **Brand FK + model** — lần này brand là plain varchar, defer Brand entity
- **Optimistic locking (version field)** — last-write-wins được chấp nhận MVP
- **Hard delete UI** — chỉ qua Django Admin
- **i18n field** (name_vi vs name_en) — defer Phase 2

## Dependencies

**Depends on**:
- ✅ Backend scaffold (commit `ca23db4`) đã có
- ✅ Frontend scaffold đã có
- ✅ `apps/core` (BaseModel, AuditLog) đã có
- Local Docker (postgres + redis + minio) running

**Blocks**:
- Feature `02-variant-crud` cần Product FK target
- Feature `03-product-media` cần Product entity
- Feature `04-channel-listing-shopee` cần Product info để push

## Success Criteria

- ✅ All 10 AC pass (manual UAT + automated)
- ✅ Test coverage ≥ 80% cho `apps/catalog` (BE) và `src/lib/api/products.ts` + form (FE)
- ✅ Code review pass (skill `code-review` — không có 🔴 finding)
- ✅ E2E Playwright happy path green
- ✅ Manual QA checklist hoàn thành
- ✅ API p95 < 500ms với seed 1000 record
- ✅ `python manage.py check --deploy` clean
- ✅ `npm run build` clean (production build)

---

*Created by skill: `ba-spec` | Date: 2026-05-26*
