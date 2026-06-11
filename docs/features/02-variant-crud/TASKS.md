# TASKS — Variant CRUD (02-variant-crud)

Breakdown thành ~1-2h chunks. Tổng ~25h. Mirror cấu trúc Product CRUD (3 phase: BE → FE → review/commit).

## Phase 1 — Backend (BE)

### Task 1.1 — Scaffold `apps/skus` app (0.5h)
- Tạo skeleton: `apps/skus/{__init__.py, apps.py, admin.py, urls.py}` rỗng
- Subfolder: `models.py`, `exceptions.py`, `utils.py`, `services/`, `selectors/`, `serializers/`, `views/`, `migrations/`, `tests/`
- Add `"apps.skus"` vào `LOCAL_APPS` ở `config/settings/base.py`
- Mount `path("api/v1/skus/", include("apps.skus.urls"))` ở `config/urls.py` (urls rỗng tạm)
- `python manage.py check` → pass

### Task 1.2 — Variant model + migration (1.5h)
- `apps/skus/models.py` — class `Variant(BaseModel)` với toàn bộ field theo DESIGN.md (3 axis, sku, sequence_no, name, prices, status, attributes)
- CheckConstraints (base_price ≥0, cost_price isnull|≥0, sequence_no ≥1)
- Meta indexes: status+deleted_at, product+sequence_no, GIN attributes
- `python manage.py makemigrations skus` → migration `0001_initial`
- Sửa migration đó: thêm `dependencies = [("catalog","0001_initial"), ("core","0002_postgres_extensions")]`
- Append `RunSQL` operations: 6 indexes (partial unique sku, combo, sequence + GIN trgm name/sku + GIN jsonb attributes)
- `python manage.py migrate` chạy được trên dev DB

**Deliverable**: model tạo bảng `skus_variants` với 6 indexes; migrate OK.

### Task 1.3 — Utils + exceptions (1h)
- `apps/skus/utils.py`: `compute_sku`, `validate_sku_length`, `compute_variant_name`, hằng số `SKU_LEN_MIN/MAX`, `MAX_BATCH`
- `apps/skus/exceptions.py`: 10 exceptions (xem DESIGN.md), tất cả extend `APIException`, có `default_code` cho `error_code` mapping
- Unit test sơ bộ `tests/test_utils.py`: compute_sku, validate length 12/24 boundaries

**Deliverable**: helper testable; exceptions có default_code đúng.

### Task 1.4 — Selectors (1h)
- `apps/skus/selectors/variants.py`:
  - `get_variant(*, variant_id, include_deleted=False)` — catch DoesNotExist/ValueError/ValidationError → `VariantNotFoundError`
  - `list_variants(*, product_id=None, search="", status=None, show_archived=False, ordering="sequence_no")` — `.select_related("product")`, filters
- Unit test cho selector (happy + missing + filter)

**Deliverable**: selectors thuần read, no side effects.

### Task 1.5 — Service: variant_create / update / soft_delete / restore (2h)
- `apps/skus/services/variants.py`:
  - `variant_create` — keyword-only, `@transaction.atomic`, `select_for_update(Product)`, validate product status, compute sequence_no, gen SKU, gen name, create + audit log
  - `variant_update` — chỉ accept base_price/cost_price/status/attributes; nếu user gửi field immutable → raise `VariantFieldImmutableError`
  - `variant_soft_delete` — set deleted_at, audit log
  - `variant_restore` — clear deleted_at; nếu combo đã tồn tại active → `RestoreConflictError`
- `_raise_for_integrity(e)` mapping unique violation → domain exception

**Deliverable**: 4 service function với keyword-only args + audit log đầy đủ.

### Task 1.6 — Service: variant_bulk_create_matrix (2h)
- `apps/skus/services/variants.py` (tiếp):
  - Validate input arrays non-empty, total ∈ [1, 100], no duplicate code3 trong materials/colors, no duplicate trong sizes (case-insensitive)
  - `select_for_update(Product)`; check product status/deleted
  - Aggregate `Max(sequence_no)` để lấy `last_seq`
  - Loop tổ hợp → build list Variant instances (chưa save), gen SKU + name + assign sequence_no liên tiếp
  - Pre-check combo trùng DB (filter case-insensitive): nếu có overlap → `DuplicateVariantComboError` với danh sách combo trùng
  - `Variant.objects.bulk_create(list)`
  - Audit log từng variant (loop sau bulk_create)
- Edge handle: validate sku length cho mỗi combo (sku_root quá dài + size dài có thể vượt 24)

**Deliverable**: matrix service tạo atomic N×M×P variants với sequence không gap.

### Task 1.7 — Serializers (1h)
- `apps/skus/serializers/variants.py`:
  - `VariantInputSerializer` (single create)
  - `VariantUpdateSerializer` (PATCH, chỉ 4 field)
  - `VariantMatrixInputSerializer` + nested `AxisEntry`; `validate` check total ≤ 100
  - `VariantOutputSerializer` (full)
  - `VariantListItemSerializer` (narrow cho list)
- Regex validation cho code3 + size_preset; uppercase code3 trong `validate_<field>`

**Deliverable**: 5 serializers; unit test format regex.

### Task 1.8 — Views + URLs (1h)
- `apps/skus/views/variants.py`:
  - `VariantViewSet(GenericViewSet)` với `IsAuthenticated`, `http_method_names` không PUT
  - Methods: `list`, `retrieve`, `create`, `partial_update`, `destroy`, `@action restore`
  - Thin — delegate service/selector, dùng đúng serializer cho input vs output
  - filter: parse `product`, `status`, `search`, `show_archived` query params; gọi `list_variants`
- `apps/skus/urls.py`: SimpleRouter register `variants`
- `apps/skus/views/matrix.py` (hoặc cùng file): `ProductVariantMatrixView(APIView)` cho endpoint nested
- `config/urls.py`: add path matrix endpoint

**Deliverable**: 7 endpoints work qua Swagger.

### Task 1.9 — Admin (1h)
- `apps/skus/admin.py`: `ProductAdmin` pattern (override `get_queryset` để dùng `all_objects`, bulk actions soft_delete/restore)
- Search fields, list_filter, readonly_fields, list_display

**Deliverable**: Variant quản lý được qua `/admin/skus/variant/`.

### Task 1.10 — BE tests: models + utils (0.5h)
- `tests/test_models.py`: tạo Variant qua factory, kiểm CheckConstraint reject negative price
- `tests/test_utils.py`: compute_sku 12/22/23/24 char boundaries, regex match

### Task 1.11 — BE tests: services (2h)
- `tests/factories.py`: `VariantFactory` (gắn ProductFactory đã có)
- `tests/test_services.py`:
  - `test_variant_create_happy_path`
  - `test_sku_length_in_range_BR002` (parametrized 4-5 case)
  - `test_audit_log_created_on_create`
  - `test_duplicate_combo_raises_409`
  - `test_product_archived_blocks_create`
  - `test_concurrent_creation_no_sku_collision` — `@pytest.mark.django_db(transaction=True)` + 5 threads → 5 SKU unique
  - `test_variant_update_immutable_field_rejected`
  - `test_variant_update_audit_log_diff`
  - `test_soft_delete_then_restore`
  - `test_restore_conflict_when_combo_already_active`
  - `test_matrix_2x3x3_creates_18_variants`
  - `test_matrix_explosion_blocked_at_101`
  - `test_matrix_duplicate_input_rejected`
  - `test_matrix_combo_overlap_with_existing_db_rejected`

**Deliverable**: coverage `apps.skus.services` ≥ 90%.

### Task 1.12 — BE tests: API (2h)
- `tests/test_api.py`:
  - Unauthenticated → 401
  - `test_create_returns_201_minimal`
  - `test_create_invalid_code3_returns_400`
  - `test_list_with_filters`
  - `test_pagination`
  - `test_patch_immutable_field_returns_400_error_code`
  - `test_delete_then_restore_endpoints`
  - `test_show_archived_filter`
  - `test_bulk_matrix_endpoint_201`
  - `test_bulk_matrix_returns_count_and_created_list`
  - `test_bulk_matrix_too_large_returns_400_error_code`
  - `test_bulk_matrix_product_archived_returns_400`
  - `test_bulk_matrix_combo_overlap_returns_409`

**Deliverable**: coverage tổng `apps.skus` ≥ 80%.

---

## Phase 2 — Frontend (FE)

### Task 2.1 — Types + Zod schemas (1h)
- `src/lib/types/variant.ts`: `Variant`, `VariantInput`, `VariantUpdateInput`, `VariantMatrixInput`, `AxisEntry`, `VariantList`
- `src/lib/schemas/variant.ts`: `variantInputSchema`, `variantUpdateSchema`, `variantMatrixInputSchema`, `axisEntrySchema`, `code3Schema`, `sizePresetSchema`
- Unit test schema (boundary + regex): `__tests__/variant.test.ts`

**Deliverable**: type-safe + zod validation match BE constraints 1:1.

### Task 2.2 — API client + React Query hooks (1h)
- `src/lib/api/variants.ts`: methods `list`, `get`, `create`, `update`, `delete`, `restore`, `createMatrix` qua `apiClient`
- `src/lib/hooks/use-variants.ts`:
  - `variantKeys = { all, list(productId, filters), detail(productId, vid) }`
  - `useVariants(productId, filters)`
  - `useVariant(productId, vid)`
  - `useCreateVariant(productId)`
  - `useUpdateVariant(productId, vid)`
  - `useDeleteVariant(productId, vid)`
  - `useRestoreVariant(productId, vid)`
  - `useCreateVariantMatrix(productId)`
  - Mỗi mutation: onSuccess invalidate `variantKeys.list(productId)`, toast.success; onError toast.error(extractErrorMessage)
- Reuse `extractErrorMessage` từ products hook

**Deliverable**: hooks dùng được trong components.

### Task 2.3 — Variant list page + table (2h)
- `src/app/admin/products/[id]/variants/page.tsx` — server shell, render `<VariantsListClient productId>`
- `_components/variants-list-client.tsx` — TanStack Table với columns
- `_components/columns.tsx` — sku, name, material/color/size, base_price, status, sequence_no, actions
- `_components/variants-toolbar.tsx` — search input (debounced), status dropdown, show_archived toggle, button "Thêm variant" + "Thêm matrix"
- Loading state (skeleton), empty state (chưa có variant)

**Deliverable**: list + filter + pagination chạy.

### Task 2.4 — Single variant form + new page (1.5h)
- `src/components/variants/variant-single-form.tsx` — RHF + zod, props `productId`, `mode`, `defaults`
  - Field: material_name + material_code3, color_name + color_code3, size_preset, base_price, cost_price, status
  - Submit handler call `useCreateVariant` hoặc `useUpdateVariant`
- `src/app/admin/products/[id]/variants/new/page.tsx` — render form mode="create"

**Deliverable**: single CRUD end-to-end FE → BE.

### Task 2.5 — Variant edit page (1.5h)
- `src/app/admin/products/[id]/variants/[vid]/page.tsx` — server shell
- `_components/variant-edit-client.tsx` — `useVariant` prefill, render `<VariantSingleForm mode="edit" defaults>`
- Trong edit mode, disable + visually grey-out: material_*, color_*, size_preset, sku (read-only); chỉ editable: base_price, cost_price, status, attributes

**Deliverable**: edit page hoạt động, immutable field disabled.

### Task 2.6 — Matrix form UI (3h)

Đây là task FE phức tạp nhất. Chia nhỏ:

- 2.6.a — `<AxisChipInput name="materials">` component (1h): UI chips, click add → mini-form (name + code3), validate code3 regex, list chips removable
- 2.6.b — `<AxisChipInput name="colors">` (reuse component 2.6.a) — cùng pattern
- 2.6.c — `<AxisChipInput name="sizes">` variant: chỉ 1 string per chip (không có code3)
- 2.6.d — `src/components/variants/variant-matrix-form.tsx` (1h): tổng hợp 3 axis input + pricing input + real-time count + button Preview
  - Validate via `variantMatrixInputSchema`
  - Disable submit nếu total > 100; warn toast nếu > 50
- 2.6.e — `src/components/variants/variant-matrix-preview-table.tsx` (1h): compute combos client-side, render table với SKU placeholder `"<sku_root>-<MAT>-<COL>-<SIZE>-XX"` (BE sẽ gen sequence)
  - Hai trạng thái: "edit axis" (back button) | "confirm" (call useCreateVariantMatrix)
- `src/app/admin/products/[id]/variants/new-matrix/page.tsx` — render form

**Deliverable**: matrix flow: input axis → preview → submit → 6+ variants tạo thành công.

### Task 2.7 — Delete confirm + restore (0.5h)
- Reuse `delete-confirm-dialog.tsx` pattern từ products
- Trong list row actions: nếu deleted_at != null → nút "Restore"; nếu null → nút "Xoá"

### Task 2.8 — Link từ Product detail → Variants (0.5h)
- `src/app/admin/products/[id]/_components/product-edit-client.tsx`: thêm button "Quản lý variants" / link tới `/variants`
- Header trang variants có breadcrumb: Products > {product.name} > Variants

### Task 2.9 — FE tests (1.5h)
- `src/lib/schemas/__tests__/variant.test.ts` — zod cases
- `src/lib/hooks/__tests__/use-variants.test.tsx` — useVariants + useCreateVariant + useCreateVariantMatrix với MSW
- `src/test/msw/handlers.ts` — thêm handlers cho 7 endpoints variants

### Task 2.10 — E2E Playwright (1h)
- `frontend/e2e/variants.spec.ts`:
  - Login → vào product có sẵn → vào variants list (empty)
  - Click "Thêm matrix" → fill 2 materials × 2 colors × 1 size = 4 variants → Preview → Tạo → list có 4 dòng
  - Edit 1 variant base_price → save → list update
  - Delete 1 → list giảm; toggle show_archived → có lại

**Deliverable**: E2E pass headless trên CI.

---

## Phase 3 — Verify + commit

### Task 3.1 — BE manual smoke (1h)
- Chạy `python manage.py runserver`, qua Swagger:
  - POST single variant → check SKU format
  - POST bulk-matrix 2×2×2 → check 8 variants, sequence 1-8
  - PATCH base_price → check audit_log
  - DELETE → check soft delete + list filter
- Manual race test (optional): 2 tab Swagger gọi cùng product POST → no collision

### Task 3.2 — FE manual smoke + matrix UX (1h)
- Khởi động `npm run dev`, test:
  - Tạo product mới (có sẵn)
  - Add matrix 3 material × 3 color × 2 size = 18 → preview đúng → tạo → list có 18 dòng
  - Verify SKU pattern + sequence
  - Edit + delete + restore
- Cross-browser: Chrome (chính), check mobile responsive cho list page

### Task 3.3 — `code-review` skill (BE) → commit (1h)
- Invoke skill `code-review` với scope `apps/skus`
- Resolve Critical/Major findings
- Commit: `feat(skus): add Variant CRUD backend with matrix bulk creator`

### Task 3.4 — `code-review` skill (FE) → commit (1h)
- Invoke `code-review` với scope FE variants code
- Resolve findings
- Commit: `feat(skus): add Variant admin UI with matrix form`

### Task 3.5 — CHANGELOG + status (0.5h)
- `docs/features/02-variant-crud/CHANGELOG.md` — what was built, deferred items, lessons learned
- `CLAUDE.md` — update status section: Phase 6 done với 2 commits mới
- Commit: `docs: update status after Variant CRUD feature`

---

## Tóm tắt

| Phase | Giờ |
|---|---|
| Phase 1 — Backend (12 task) | ~15h |
| Phase 2 — Frontend (10 task) | ~12h |
| Phase 3 — Verify + commit (5 task) | ~4.5h |
| **Total** | **~31.5h** |

(So với estimate ANALYSIS ~23h: thực tế padding +37% cho test viết kỹ + matrix UI nhiều sub-component + manual smoke.)

## Pipeline handoff sau khi user confirm

1. **`db-schema`** — Task 1.1 + 1.2 (model + migration + indexes)
2. **`django-backend`** — Task 1.3 → 1.9 (utils, exceptions, services, selectors, serializers, views, urls, admin)
3. **`test-generator`** — Task 1.10 → 1.12 + Task 2.9 + 2.10
4. **`nextjs-frontend`** — Task 2.1 → 2.8 (types, hooks, pages, components)
5. **`code-review`** + commit — Task 3.3, 3.4, 3.5

Task 3.1, 3.2 (manual smoke) là việc của user, không qua skill.
