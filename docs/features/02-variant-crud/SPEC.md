# SPEC — Variant CRUD (02-variant-crud)

## Mục tiêu (Why)
Cho phép Catalog Manager tạo, đọc, sửa, xoá **Variant** — phiên bản bán được của một Product, định danh bởi tổ hợp 3 trục: **material × color × size_preset**. Có cả **single CRUD** và **Matrix bulk creator** (sinh N×M×P variants 1 lần). SKU auto-gen theo BR-002 (giản lược, bỏ CAT3).

## Quyết định chốt PHA 2

| Mục | Lựa chọn |
|---|---|
| Matrix UI v1 | Generate + preview (read-only), không edit per-cell. base_price + cost_price chung cho cả batch |
| Material/Color code3 | User nhập tay 2 field: `name` (free string) + `code3` (uppercase alphanumeric 2-4) |
| Variant `name` | Auto-gen `"{product.name} - {material_name} {color_name} {size_preset}"`, không cho edit v1 |
| SKU pattern | `<sku_root>-<MAT3>-<COLOR3>-<SIZE>-<NN>` (12-22 chars, không CAT3 — migrate sau khi có Category) |
| Status enum | `draft / active / archived` (giống Product) |
| Soft delete + restore + audit | Giống Product (`deleted_at`, BR-009 audit log) |
| Block tạo trên Product archived | Có — return 400 `PRODUCT_ARCHIVED` |

## User flow

### Flow A — Tạo single variant
1. CM ở `/admin/products` → click vào 1 product → vào trang detail Product
2. Click nút **"Quản lý variants"** → đi tới `/admin/products/<id>/variants`
3. Click **"Thêm variant"** → form 1 variant (`/variants/new`)
4. Nhập: material (name + code3), color (name + code3), size_preset, base_price, cost_price (optional), status (default draft)
5. Submit → BE validate → auto-gen SKU `<sku_root>-<MAT3>-<COL3>-<SIZE>-<NN>` → audit log → 201
6. Toast success → quay về variant list, dòng mới xuất hiện

### Flow B — Tạo matrix bulk
1-2. Như Flow A đến trang variant list
3. Click **"Thêm matrix"** → `/admin/products/<id>/variants/new-matrix`
4. Form gồm 3 nhóm chip input:
   - **Materials**: thêm nhiều cặp (name + code3), vd `("PLA","PLA") ("PETG","PET")`
   - **Colors**: thêm nhiều cặp (name + code3), vd `("Red","RED") ("Blue","BLU") ("Green","GRN")`
   - **Sizes**: thêm nhiều string, vd `S, M, L`
5. Phía dưới: `base_price` (apply cho cả batch), `cost_price` (optional), `status` (default draft)
6. Tổng = `len(materials) × len(colors) × len(sizes)` hiển thị real-time: *"Sẽ tạo 18 variants"*
7. Cảnh báo toast nếu tổng > 50: *"Bạn sắp tạo X variants — chắc chứ?"*. Disable submit nếu tổng > 100.
8. Click **"Preview"** → table N×M×P rows: name, SKU (computed client-side, có thể khác BE 1 ít do sequence chưa biết), material/color/size
9. Click **"Tạo tất cả"** → POST matrix endpoint → BE atomic: lock Product → gen sequence → bulk_create → audit log mỗi variant → 201
10. Quay về list, N×M×P dòng mới xuất hiện

### Flow C — Edit variant
1. Từ variant list → click row → `/admin/products/<id>/variants/<vid>` edit form
2. Cho phép sửa: `base_price`, `cost_price`, `status`, `attributes` (JSON)
3. KHÔNG cho sửa: `sku`, `material_*`, `color_*`, `size_preset`, `name`, `sequence_no` (đổi axis = đổi SKU = lộn xộn)
4. Save → BE audit log diff → 200

### Flow D — Xoá / restore
1. List → bấm icon xoá → confirm dialog → soft delete (deleted_at set), audit log
2. Toolbar có toggle "Show archived" → list bao gồm soft-deleted
3. Soft-deleted row có nút "Restore" → variant_restore → audit log

## Acceptance Criteria (Given-When-Then)

### AC1 — Tạo variant single thành công
```
Given Catalog Manager đã đăng nhập
And Product P (sku_root="DRAGON", status="active") đã tồn tại
And P chưa có variant nào
When user POST /api/v1/skus/variants/ với:
  product_id=P, material=("PLA","PLA"), color=("Red","RED"), size="M",
  base_price=150000, status="draft"
Then response 201
And variant.sku == "DRAGON-PLA-RED-M-01"
And variant.sequence_no == 1
And variant.name == "Dragon Figure - PLA Red M"
And AuditLog 1 entry action="variant.created"
```

### AC2 — Matrix bulk tạo N×M×P
```
Given Product P chưa có variant
When POST /api/v1/catalog/products/<P_id>/variants/bulk-matrix/ với:
  materials=[("PLA","PLA"),("PETG","PET")],
  colors=[("Red","RED"),("Blue","BLU"),("Green","GRN")],
  sizes=["S","M","L"],
  base_price=150000
Then response 201, count=18
And 18 variants được tạo
And sequence_no chạy 1→18 (không gap)
And mỗi SKU unique
And mỗi SKU đúng pattern length 12-22
And 18 AuditLog entries action="variant.created"
```

### AC3 — Race condition không trùng SKU
```
Given 5 thread đồng thời gọi variant_create cho cùng Product P
When run concurrent
Then 5 variants tạo thành công
And SKU sequence là 01-05 (unique)
And không IntegrityError
And không duplicate sequence_no
```
(Test bằng `pytest.mark.django_db(transaction=True)` + threading)

### AC4 — Cap variant explosion
```
Given matrix 10×10×10 = 1000 combos
When submit
Then 400 với error_code="VARIANT_BATCH_TOO_LARGE"
And payload: {"max":100,"requested":1000}
```

### AC5 — Block on Product archived
```
Given Product P status="archived"
When tạo variant trên P (single hoặc matrix)
Then 400 error_code="PRODUCT_ARCHIVED"
And không có variant nào được tạo
```

### AC6 — Block trùng combo per product
```
Given Variant V1 đã tồn tại với product=P, material_code3="PLA", color_code3="RED", size="M"
When tạo V2 cùng product=P, code3 cùng (case-insensitive), size cùng
Then 409 error_code="DUPLICATE_VARIANT_COMBO"
```

### AC7 — Matrix có trùng combo nội bộ
```
Given matrix có 2 material PLA giống nhau (do user thêm trùng)
When submit
Then 400 error_code="DUPLICATE_IN_MATRIX_INPUT"
And không variant nào được tạo
```

### AC8 — SKU length validate BR-002
```
Given sku_root="ABCDEFGH" (8 chars, max)
And material_code3="PETG" (4 chars)
And color_code3="ORG" (3 chars)
And size_preset="XL" (2 chars)
When compute SKU
Then SKU = "ABCDEFGH-PETG-ORG-XL-01" length 22 ∈ [12,24] ✓
```

### AC9 — Edit chỉ giới hạn field cho phép
```
Given Variant V tồn tại
When PATCH với material_code3="ABS"
Then 400 error: "material_code3 immutable after creation"
When PATCH với base_price=200000
Then 200, base_price=200000, AuditLog diff {"base_price":[150000,200000]}, SKU unchanged
```

### AC10 — Search & filter
```
Given 20 variants trong DB (mix material PLA/PETG, status draft/active)
When GET /variants/?search=PLA&status=active&product=<id>
Then trả về subset đúng (sku/name có "PLA" + status="active" + product khớp)
And pagination chuẩn (page_size=20)
```

### AC11 — Soft delete + restore + show_archived
```
Given Variant V status="active"
When DELETE /variants/<id>/
Then 204, V.deleted_at set
And GET /variants/ KHÔNG bao gồm V
And GET /variants/?show_archived=true bao gồm V
When POST /variants/<id>/restore/
Then 200, V.deleted_at=null
And AuditLog "variant.deleted" + "variant.restored"
```

### AC12 — Permission (v1 = IsAuthenticated, RBAC defer)
```
Given user chưa login
When POST /variants/
Then 401
Given user đã login (bất kỳ role nào, v1 không phân quyền)
When POST /variants/
Then 201 (nếu hợp lệ)
```
> Defer: RBAC chính thức (Catalog Manager + Designer + Super Admin được tạo; Cashier read-only) sẽ làm ở feature `accounts/RBAC`.

## Edge cases

| # | Case | Xử lý |
|---|---|---|
| E1 | Material name có dấu tiếng Việt ("Acid Polylactic") | OK (UTF-8); code3 vẫn alphanumeric ASCII |
| E2 | Size_preset = "12cm" (chữ + số) | OK nếu regex `^[A-Za-z0-9]{1,8}$` |
| E3 | base_price âm | 400 (zod FE + serializer BE) |
| E4 | cost_price > base_price (margin âm) | Cho phép, FE hiển thị warning toast (không block) |
| E5 | Matrix với 0 axis value ở 1 trục | 400 `EMPTY_MATRIX` |
| E6 | Concurrent matrix submit cùng Product | Cả 2 thành công với sequence disjoint (lock Product) |
| E7 | Restore variant khi product status=archived | Cho restore, variant giữ status cũ (kể cả active). Document: lúc đó variant không "bán" được nhưng vẫn tồn tại. Defer fix sau. |
| E8 | Delete Product có variants | Product chỉ soft delete (`deleted_at`); variant FK on_delete=PROTECT chặn hard delete; soft delete Product không cascade xuống variants. |
| E9 | Concurrent edit cùng variant (User A và B cùng PATCH) | Last-write-wins (default). Defer optimistic locking. |
| E10 | sku_root product change sau khi có variants | KHÔNG: Product `sku_root` cũng nên immutable (đã được Product CRUD enforce gián tiếp — TODO confirm); SKU variants giữ nguyên |

## Out of scope (defer)

| Item | Lý do defer | Feature kéo theo |
|---|---|---|
| License check BR-003 | Chưa có Design Files | `03-design-files` |
| design_file_id FK | Cần Design Files | `03-design-files` |
| Cost calc tự động BR-005 | Cần Material model + electricity | `XX-materials`, `XX-costing` |
| Channel push BR-004 (Tiki 2-axis) | Cần Channel feature | `XX-channels-shopee/lazada/tiki` |
| Inventory stock_on_hand BR-006/007 | Chưa có Inventory | `XX-inventory` |
| Barcode EAN-13 BR-010 | Chưa có POS | `XX-pos` |
| 3D preview BR-008 | Cần Design Files + STL/GLB | `03-design-files` |
| RBAC chặt | Defer toàn dự án | `accounts/RBAC` |
| Bulk import CSV | Defer | post-MVP |
| Per-cell edit trong matrix | Defer v1.1 | follow-up |
| Optimistic locking concurrent edit | Defer | post-MVP |
| Flat `/admin/variants` (cross-product) list | v1 chỉ nested under product | v1.1 |

## Business rules applied / deferred

| BR | Status v1 |
|---|---|
| BR-001 SKU unique (case-insensitive) | ✅ Apply — partial unique index `LOWER(sku) WHERE deleted_at IS NULL` |
| BR-002 SKU pattern + length 12-24 | ✅ Apply (simplified: bỏ CAT3, dùng sku_root làm prefix) |
| BR-003 License blocks active | ❌ Defer |
| BR-004 Tiki 2-axis | ❌ Defer (channel feature) |
| BR-005 Cost = material+electricity+... | ❌ Defer (chỉ field cost_price tự nhập) |
| BR-006 Stock sync < 30s | ❌ Defer (inventory) |
| BR-007 Safety stock buffer | ❌ Defer |
| BR-008 STL >100MB cần GLB | ❌ Defer |
| BR-009 Audit log mọi state change | ✅ Apply — variant.created/updated/deleted/restored |
| BR-010 EAN-13 prefix | ❌ Defer (POS) |

## Dependencies

- ✅ Product CRUD (commits `91ddf64`, `c14c9f1`)
- ✅ Core models (`BaseModel`, `AuditLog`)
- ✅ Postgres extensions migration (pg_trgm, btree_gin)
- ⏳ Material model — **không** dependency v1 (dùng string)
- ⏳ Design Files — **không** dependency v1 (defer license)
- ⏳ Category — **không** dependency v1 (bỏ CAT3 khỏi SKU pattern)

## Definition of Done

- [ ] BE code implemented + ruff + mypy pass
- [ ] BE test coverage ≥ 80% trên `apps.skus` (target 90%+ theo precedent Product 97%)
- [ ] Race condition test pass: 5 thread concurrent → 5 SKU unique
- [ ] Matrix test pass: 2×3×3 = 18 variants tạo thành công atomic
- [ ] FE code typecheck + lint pass
- [ ] FE unit tests pass (schema, hooks)
- [ ] E2E Playwright: tạo product → matrix 2×2 → 4 variants xuất hiện
- [ ] Manual smoke: tạo 30 variants/product trong < 1 phút
- [ ] Code review (skill `code-review`) — no Critical/Major blocking
- [ ] CHANGELOG.md + CLAUDE.md status updated
- [ ] 2 commits: `feat(skus): add Variant CRUD backend` + `feat(skus): add Variant admin UI` (mirror Product pattern)
