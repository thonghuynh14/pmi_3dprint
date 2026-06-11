# Changelog: Variant CRUD (feature 02)

## 2026-06-11 — Phase 2: Frontend (Variant admin UI)

### Added
- **List page**: `admin/products/[id]/variants` — TanStack Table, search (debounce 300ms) + status filter + show-archived switch + pagination, URL-state sync, skeleton/error/empty states.
- **Single create/edit form**: `variant-form.tsx` — RHF + zod, axes immutable on edit mode, dirty-fields PATCH (chỉ 4 field mutable: base_price/cost_price/status/attributes), BE field error mapping qua extractErrorMessage (detail-dict shape support).
- **Matrix bulk creator**: `variant-matrix-form.tsx` (~480 dòng, 2 phase input→preview) + `variant-matrix-preview-table.tsx`. useState cho axes dynamic (RHF+useFieldArray phức tạp hơn cho 2-field entries). Enter-key add chip. Warn > 50 qua `window.confirm()`, hard cap = `MAX_VARIANT_BATCH=100` disable submit. SKU placeholder `-XX` (BE assign sequence_no atomic).
- **Delete confirm dialog**: SKU-based confirmation, undo toast.
- **Restore action**: từ row của variant đã archived.
- **Link "Quản lý variants"**: từ Product detail page sang variants list.
- **API + hooks layer**: `lib/api/variants.ts`, `lib/hooks/use-variants.ts` (variantKeys factory + 6 mutation hooks + extractErrorMessage handle detail-dict), `lib/schemas/variant.ts` (3 schema: input/update/matrix với refine N×M×P ≤ 100), `lib/types/variant.ts`.
- **Tests**: Vitest 49 (36 zod + 13 hooks via MSW handlers cho 7 variant endpoint). Playwright matrix flow spec (2×2×1 → 4 variants, login → create product → matrix → cleanup) — file viết sẵn, chưa chạy E2E.

### Verified
- 66 unit tests pass (17 product + 49 variant) · `tsc --noEmit` clean · 0 `any` / 0 `key={index}` / 0 sửa shadcn UI.

### Deferred (tracked, không block MVP)
- **E2E run**: Playwright spec viết xong nhưng chưa chạy (cần Docker daemon up). Sẽ chạy ở smoke test trước khi cut MVP.
- **AlertDialog cho confirm > 50**: hiện dùng `window.confirm()` native — đủ cho v1, nâng cấp shadcn AlertDialog khi có nhu cầu.
- **i18n**: strings tiếng Việt hardcode (next-intl đã cài, chưa wire) — SPEC out-of-scope.
- **`variant.name` overflow 200 chars** ở edge case (product name dài + material+color+size name dài): Minor — defer, BE truncate hoặc validate sau.

### Commit
- `18e476b feat(skus): add Variant admin UI`

---

## 2026-06-11 — Phase 1: Backend (Variant CRUD API + matrix bulk)

### Added
- `apps/skus`: Variant model (UUID + soft delete + audit + 8 CheckConstraints), migration 0001 (partial unique index sku/combo/sequence_no `WHERE deleted_at IS NULL`, GIN trgm name/sku, GIN jsonb_path_ops attributes).
- `apps/skus/utils.py`: `compute_sku` theo BR-002 pattern `<sku_root>-<MAT3>-<COLOR3>-<SIZE>-<NN>`, `validate_sku_length` (12-24), `MAX_BATCH=100`.
- Service layer: 10 exceptions (BatchTooLarge/SkuLengthInvalid/FieldImmutable override `__init__` cho detail-dict payload), selectors (get/list), services (create/update/soft_delete/restore + `variant_bulk_create_matrix`).
- **Race protection**: `select_for_update(Product)` lock + `_next_sequence_no` qua `Variant.all_objects` (tránh NN re-use sau soft delete). Defense-in-depth: partial unique index `_INTEGRITY_ERROR_MAP` map sang domain exception.
- **Atomic matrix**: pre-check combo overlap trước bulk_create, all-or-nothing, MAX_BATCH=100.
- **Immutable field enforcement** (3 layers): serializer.validate / service `_UPDATABLE_FIELDS` / DB partial unique.
- `_jsonify(data)` helper dùng `DjangoJSONEncoder` cho `AuditLog.changes` (workaround Decimal serialize — TODO move sang core).
- DRF: 5 serializer (Input/Update/MatrixInput/Output/ListItem), VariantFilter, VariantViewSet + ProductVariantMatrixView (nested APIView).
- Django Admin: VariantAdmin (axes readonly, bulk soft-delete/restore actions).
- Tests: 99 pass (96% coverage) — model/utils/selector/service/api + race condition (5 threads concurrent gen SKU, 0 collision, 5 unique seq).

### Commit
- `9414a2b feat(skus): add Variant CRUD backend with matrix bulk creator`
