# Changelog: Product CRUD (feature 01)

## 2026-05-27 — Phase 2: Frontend (Product admin UI)

### Added
- **Auth (dev)**: `(auth)/login` page — POST simplejwt `/auth/token/`, lưu access localStorage. Defer proper auth UI (OQ-2).
- **Admin shell**: `admin/layout.tsx` — header + nav + logout, client-side auth guard.
- **List page**: `admin/products` — TanStack Table, search (debounce 300ms) + status filter + show-archived switch + pagination, URL-state sync, skeleton/error/empty states.
- **Create/Edit form**: `product-form.tsx` (shared) — RHF + zod, slug auto-fill (VN-aware), tags comma-separated, attributes JSON, dirty-fields PATCH (AC-7), BE field error mapping.
- **Detail/Edit page**: `admin/products/[id]` — client fetch (includeDeleted), delete/restore.
- **Shared** `DeleteConfirmDialog` (list + edit), undo toast.
- **API layer**: `lib/api/products.ts`, `lib/hooks/use-products.ts` (productKeys factory), `lib/schemas/product.ts` (zod), `lib/types/product.ts`.
- **shadcn components**: input, label, textarea, select, badge, dialog, table, dropdown-menu, switch, skeleton, form (hand-written).
- **Tests**: Vitest (12 schema + 5 hooks via MSW) + Playwright e2e (full CRUD happy path).

### Verified
- 17 unit tests + 1 e2e pass · `tsc --noEmit` clean · `npm run lint` clean · `npm run build` clean.
- Manual QA: VN accents (`Tượng Phật Di Lặc` → `tuong-phat-di-lac`), audit log create/update/delete, perf **p95=273ms** với 1004 products (target <500ms).

### Deferred (tracked, không block MVP)
- **Token storage**: access token ở localStorage (XSS risk). Mitigation: internal tool, TTL 15'. → chuyển in-memory + httpOnly refresh cookie khi build feature `accounts`.
- **Refresh flow**: login chỉ lưu access; `/auth/refresh/` interceptor chưa hoạt động (chưa set refresh cookie) → access hết hạn phải login lại.
- **i18n**: strings tiếng Việt hardcode (next-intl đã cài, chưa wire) — SPEC out-of-scope.
- **Auth guard**: client-side only (page flash) — middleware guard cùng feature `accounts`.
- **CSP headers**: chưa set `next.config.mjs`.
- **File size**: `product-form.tsx` 372 dòng, `products-list-client.tsx` 212 dòng (>200) — cân nhắc tách field-group sau.

### Route fix
- `(admin)` route group → đổi thành `admin` segment để URL có prefix `/admin/products`.

---

## 2026-05-27 — Phase 1: Backend (Product CRUD API)

### Added
- `apps/catalog`: Product model (UUID + soft delete + audit), migration 0001 (partial unique LOWER(slug/sku_root), GIN trgm/jsonb/array indexes, CHECK constraints).
- `core/0002_postgres_extensions` migration (extensions cho test DB fresh).
- Service layer: exceptions, selectors (get/list), services (create/update/soft_delete/restore + audit).
- DRF: Input/Output/ListItem serializers, ProductFilter, ProductViewSet (PUT tắt, @action restore), JWT auth endpoints.
- Django Admin: ProductAdmin (all_objects queryset, bulk soft-delete/restore actions).
- Tests: 105 pass, 97% coverage (model/selector/service/viewset/admin + race condition).

### Commit
- `91ddf64 feat(catalog): add Product CRUD backend`
