# Tasks: CRUD Product

> Breakdown thành tasks 1-2h. Mỗi task có **deliverable test-able**.
> Trigger skill mapping ở cuối từng task.

## Status legend
- ⬜ Not started
- 🟡 In progress
- ✅ Done
- ⏸️ Blocked

## Summary
- **Total estimated**: ~15.5h (≈ 2 working days)
- **Started**: TBD
- **Target done**: TBD

---

## Phase 1: Backend foundation (BE)

### Task 1.1: Create `apps/catalog` skeleton + Product model + migration ⬜
**Estimate**: 1.5h
**Deliverable**:
- `python manage.py migrate catalog` chạy thành công
- `python manage.py shell` → `from apps.catalog.models import Product; Product.objects.create(...)` work
- `\d catalog_products` trong psql hiển thị đủ columns + indexes

**Steps**:
1. `mkdir backend/apps/catalog && touch backend/apps/catalog/{__init__.py,apps.py,models.py,admin.py,exceptions.py,urls.py,filters.py}`
2. `mkdir backend/apps/catalog/{services,selectors,serializers,views,tests,migrations}` + `__init__.py` cho mỗi folder
3. `apps.py`: `CatalogConfig(name="apps.catalog", label="catalog")`
4. `models.py`:
   ```python
   class Product(BaseModel):
       class Status(models.TextChoices):
           DRAFT = "draft", "Draft"
           ACTIVE = "active", "Active"
           ARCHIVED = "archived", "Archived"

       name = models.CharField(max_length=200)
       slug = models.SlugField(max_length=220)
       sku_root = models.CharField(max_length=8)
       status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
       short_description = models.TextField(blank=True, default="")
       long_description = models.TextField(blank=True, default="")
       brand = models.CharField(max_length=100, blank=True, default="")
       tags = ArrayField(models.CharField(max_length=64), default=list, blank=True)
       attributes = models.JSONField(default=dict, blank=True)

       class Meta:
           db_table = "catalog_products"
           ordering = ("-updated_at",)
           constraints = [
               models.CheckConstraint(
                   check=models.Q(sku_root__regex=r"^[A-Z0-9]{3,8}$"),
                   name="catalog_products_sku_root_format",
               ),
           ]
           indexes = [
               models.Index(fields=["-updated_at"]),
               models.Index(fields=["status"], condition=models.Q(deleted_at__isnull=True), name="catalog_products_status_alive_idx"),
           ]
   ```
5. Add `"apps.catalog"` vào `LOCAL_APPS` trong `config/settings/base.py`
6. `python manage.py makemigrations catalog`
7. Edit migration 0001: thêm raw SQL operations cho:
   - Partial unique index `LOWER(slug) WHERE deleted_at IS NULL`
   - Partial unique index `LOWER(sku_root) WHERE deleted_at IS NULL`
   - GIN trgm indexes cho `name`, `sku_root`
   - GIN index cho `attributes`, `tags`
8. `python manage.py migrate`
9. Verify trong psql

**Trigger skill**: `db-schema`

---

### Task 1.2: ProductFactory + model tests ⬜
**Estimate**: 1h
**Deliverable**: `pytest apps/catalog/tests/test_models.py` pass

**Steps**:
1. `tests/factories.py`: `ProductFactory(factory.django.DjangoModelFactory)` với Faker
2. `tests/conftest.py`: shared fixtures
3. `tests/test_models.py`:
   - `test_product_create_minimal`
   - `test_product_str_returns_name`
   - `test_sku_root_format_check_constraint_blocks_lowercase`
   - `test_sku_root_format_check_constraint_blocks_special_chars`
   - `test_slug_unique_partial_index_blocks_duplicate_alive`
   - `test_slug_unique_partial_index_allows_duplicate_if_other_deleted`
   - `test_sku_root_unique_case_insensitive`
   - `test_soft_delete_sets_deleted_at`
   - `test_default_manager_excludes_deleted`
   - `test_all_objects_manager_includes_deleted`

**Trigger skill**: `test-generator`

---

### Task 1.3: Selectors + Services + exceptions ⬜
**Estimate**: 2h
**Deliverable**: `pytest apps/catalog/tests/test_services.py test_selectors.py` pass, function-level testable từ shell

**Steps**:
1. `exceptions.py`:
   ```python
   class ProductError(Exception): ...
   class DuplicateSlugError(ProductError): ...
   class DuplicateSkuRootError(ProductError): ...
   class ProductNotFoundError(ProductError): ...
   ```
2. `selectors/products.py`:
   ```python
   def get_product(*, product_id: uuid.UUID, include_deleted: bool = False) -> Product: ...
   def list_products(*, search: str = "", status: str | None = None,
                     show_archived: bool = False,
                     ordering: str = "-updated_at") -> QuerySet[Product]: ...
   ```
3. `services/products.py`:
   ```python
   @transaction.atomic
   def product_create(*, actor: User, name: str, sku_root: str, slug: str = "",
                      status: str = "draft", short_description: str = "",
                      long_description: str = "", brand: str = "",
                      tags: list[str] | None = None,
                      attributes: dict | None = None) -> Product:
       # 1. Generate slug nếu trống
       # 2. Validate uniqueness (case-insensitive)
       # 3. Product.objects.create(...)
       # 4. audit_log(action="create", actor=actor, entity=product, changes={...})

   @transaction.atomic
   def product_update(*, actor: User, product: Product, **fields) -> Product: ...

   @transaction.atomic
   def product_soft_delete(*, actor: User, product: Product) -> None: ...

   @transaction.atomic
   def product_restore(*, actor: User, product: Product) -> Product: ...
   ```
4. Helper `_create_audit_log(action, actor, entity, changes={})` cho DRY
5. Tests:
   - `test_create_with_minimal_fields_succeeds`
   - `test_create_auto_generates_slug_from_name`
   - `test_create_with_unicode_name_generates_ascii_slug`
   - `test_create_duplicate_slug_raises_duplicate_slug_error`
   - `test_create_duplicate_sku_root_case_insensitive_raises`
   - `test_create_writes_audit_log`
   - `test_update_only_changed_fields_audited`
   - `test_soft_delete_excludes_from_default_query`
   - `test_restore_clears_deleted_at`
   - `test_list_products_search_matches_name_icontains`
   - `test_list_products_search_matches_sku_root_icontains`
   - `test_list_products_filter_status`
   - `test_list_products_show_archived_toggle`
   - `test_list_products_default_ordering_updated_at_desc`

**Trigger skill**: `django-backend`

---

### Task 1.4: Serializers + ViewSet + URLs ⬜
**Estimate**: 1.5h
**Deliverable**: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/catalog/products/` trả 200; full CRUD work qua curl/Postman

**Steps**:
1. `serializers/products.py`:
   - `ProductInputSerializer` (Serializer, không phải ModelSerializer — kiểm soát strict)
     - Fields: name, slug (optional), sku_root, status, short_description, long_description, brand, tags, attributes
     - Validators: sku_root regex, slug format, tag length, attribute keys regex
   - `ProductOutputSerializer` (ModelSerializer)
     - Fields: tất cả + nested `created_by`, `updated_by` (UserSlimSerializer)
   - `ProductListItemSerializer` — hẹp hơn cho list (loại long_description, attributes)
2. `filters.py`:
   ```python
   class ProductFilter(filters.FilterSet):
       search = filters.CharFilter(method="filter_search")
       status = filters.ChoiceFilter(choices=Product.Status.choices)
       show_archived = filters.BooleanFilter(method="filter_show_archived")
       class Meta:
           model = Product
           fields = ["status"]
   ```
3. `views/products.py`:
   ```python
   class ProductViewSet(viewsets.GenericViewSet):
       # TODO: replace IsAuthenticated với role-based khi accounts app có
       permission_classes = [IsAuthenticated]
       filterset_class = ProductFilter
       http_method_names = ["get", "post", "patch", "delete"]  # tắt PUT

       def get_queryset(self): ...
       def list(self, request): ...
       def retrieve(self, request, pk=None): ...
       def create(self, request): ...
       def partial_update(self, request, pk=None): ...
       def destroy(self, request, pk=None): ...

       @action(detail=True, methods=["post"])
       def restore(self, request, pk=None): ...
   ```
4. `urls.py`:
   ```python
   router = DefaultRouter()
   router.register("products", ProductViewSet, basename="product")
   urlpatterns = router.urls
   ```
5. `config/urls.py`: uncomment `path("catalog/", include("apps.catalog.urls"))` trong `api_v1_patterns`
6. Test bằng curl: create user superuser, login lấy JWT, curl CRUD endpoints

**Trigger skill**: `django-backend`

---

### Task 1.5: ViewSet integration tests ⬜
**Estimate**: 1.5h
**Deliverable**: `pytest apps/catalog/tests/test_viewset.py` pass với coverage ≥ 80%

**Steps**:
1. `tests/test_viewset.py` với `APIClient`:
   - `test_list_requires_auth_returns_401`
   - `test_list_returns_paginated_results`
   - `test_list_search_filters_results`
   - `test_list_status_filter_works`
   - `test_list_show_archived_includes_deleted`
   - `test_retrieve_returns_full_object`
   - `test_retrieve_deleted_returns_404`
   - `test_create_valid_returns_201_with_object`
   - `test_create_missing_required_returns_400`
   - `test_create_invalid_sku_root_format_returns_400_with_field_error`
   - `test_create_duplicate_slug_returns_400`
   - `test_create_writes_audit_log`
   - `test_partial_update_only_provided_fields_change`
   - `test_partial_update_returns_updated_object`
   - `test_delete_soft_deletes_returns_204`
   - `test_delete_writes_audit_log`
   - `test_restore_clears_deleted_at_returns_200`
   - `test_put_method_not_allowed_returns_405`
2. Race condition test:
   - `test_concurrent_create_same_sku_root_one_succeeds_one_fails` (dùng `threading.Thread` + `transaction.atomic`)

**Trigger skill**: `test-generator`

---

### Task 1.6: Django Admin registration ⬜
**Estimate**: 0.5h
**Deliverable**: `/admin/catalog/product/` hiển thị, có thể CRUD qua Django Admin

**Steps**:
1. `apps/catalog/admin.py`:
   ```python
   @admin.register(Product)
   class ProductAdmin(admin.ModelAdmin):
       list_display = ("name", "sku_root", "status", "updated_at", "deleted_at")
       list_filter = ("status",)
       search_fields = ("name", "sku_root", "slug")
       readonly_fields = ("id", "created_at", "updated_at", "deleted_at",
                          "created_by", "updated_by", "deleted_by")
       prepopulated_fields = {"slug": ("name",)}
   ```
2. Test thủ công: superuser login Django Admin, tạo + xoá product

**Trigger skill**: `django-backend`

---

## Phase 2: Frontend (FE)

### Task 2.1: shadcn add các components cần ⬜
**Estimate**: 0.25h
**Deliverable**: `src/components/ui/{input,label,textarea,select,badge,dialog,table}.tsx` tồn tại

**Steps**:
1. `cd frontend && npx shadcn@latest add input label textarea select badge dialog table`
2. Verify mỗi component compile clean: `npm run typecheck`

**Trigger skill**: `nextjs-frontend`

---

### Task 2.2: Types + zod schemas + API client ⬜
**Estimate**: 1h
**Deliverable**: `src/lib/{types,schemas,api}/product*.ts` compile clean, `import` từ test/component work

**Steps**:
1. `lib/types/product.ts`:
   ```ts
   export type ProductStatus = "draft" | "active" | "archived";
   export interface Product { /* mirror BE output */ }
   export interface ProductListItem { /* hẹp */ }
   export interface ProductListResponse { count; next; previous; results }
   ```
2. `lib/schemas/product.ts`:
   ```ts
   import { z } from "zod";
   export const productInputSchema = z.object({
     name: z.string().min(1).max(200),
     slug: z.string().regex(/^[a-z0-9-]+$/).max(220).optional().or(z.literal("")),
     sku_root: z.string().regex(/^[A-Z0-9]{3,8}$/, "3-8 ký tự hoa số"),
     status: z.enum(["draft", "active", "archived"]).default("draft"),
     short_description: z.string().default(""),
     long_description: z.string().default(""),
     brand: z.string().max(100).default(""),
     tags: z.array(z.string().max(64)).default([]),
     attributes: z.record(z.string(), z.unknown()).default({}),
   });
   export type ProductInput = z.infer<typeof productInputSchema>;
   ```
3. `lib/api/products.ts`:
   ```ts
   export async function listProducts(params: ProductListParams): Promise<ProductListResponse>
   export async function getProduct(id: string): Promise<Product>
   export async function createProduct(data: ProductInput): Promise<Product>
   export async function updateProduct(id: string, data: Partial<ProductInput>): Promise<Product>
   export async function deleteProduct(id: string): Promise<void>
   export async function restoreProduct(id: string): Promise<Product>
   ```
4. `lib/hooks/use-products.ts`:
   ```ts
   export const productKeys = { ... };
   export function useProducts(params: ProductListParams) { return useQuery(...) }
   export function useProduct(id: string) { return useQuery(...) }
   export function useCreateProduct() { return useMutation(...) }
   export function useUpdateProduct(id: string) { return useMutation(...) }
   export function useDeleteProduct() { return useMutation(...) }
   export function useRestoreProduct() { return useMutation(...) }
   ```

**Trigger skill**: `nextjs-frontend`

---

### Task 2.3: Admin layout + List page ⬜
**Estimate**: 2h
**Deliverable**: `/admin/products` hiển thị table với data thật từ API, search/filter/pagination work

**Steps**:
1. `src/app/(admin)/layout.tsx` — admin shell (header tạm bợ, nav placeholder)
2. `src/app/(admin)/products/page.tsx` (server component):
   - Parse `searchParams` (page, search, status, show_archived)
   - Render `<ProductsListClient initialParams={...} />`
3. `src/app/(admin)/products/_components/products-toolbar.tsx`:
   - Search input (debounce 300ms)
   - Status filter Select
   - "Show archived" Switch
   - "New Product" link button → `/admin/products/new`
4. `src/app/(admin)/products/_components/columns.tsx` (TanStack Table column defs):
   - name (click → /admin/products/[id])
   - sku_root (badge)
   - status (badge color)
   - tags (Badge[] truncated)
   - updated_at (date-fns relative time)
   - actions (Edit / Delete dropdown)
5. `src/app/(admin)/products/_components/products-list-client.tsx`:
   - `useProducts(params)`
   - `<DataTable columns={columns} data={data.results} />`
   - Pagination controls
   - Empty state khi `count === 0`
   - Update URL searchParams khi filter đổi
6. Manual test: chạy BE + FE, login, vào /admin/products

**Trigger skill**: `nextjs-frontend`

---

### Task 2.4: Create form page ⬜
**Estimate**: 2h
**Deliverable**: Tạo Product từ UI thành công, redirect về list, toast success

**Steps**:
1. `src/app/(admin)/products/new/page.tsx`: render `<ProductForm mode="create" />`
2. `src/app/(admin)/products/_components/product-form.tsx`:
   - useForm với zodResolver(productInputSchema)
   - Fields:
     - name (Input, auto-fill slug onBlur nếu slug trống)
     - slug (Input, có button "Auto-generate")
     - sku_root (Input, uppercase transform)
     - status (Select)
     - short_description (Textarea)
     - long_description (Textarea rows=8)
     - brand (Input)
     - tags (chip input — simple version: comma-separated Input → split)
     - attributes (textarea JSON với validate parse trên blur)
   - useCreateProduct mutation
   - onSubmit: mutate → toast → router.push('/admin/products')
   - Error handling: gắn lỗi BE field-by-field vào RHF qua setError
3. Slug helper: util `slugify(name)` dùng package `slugify` (đã có deps? check)
   - Note: nếu chưa có, dùng implementation thủ công đơn giản (lowercase + replace non-alphanum + trim hyphen)
4. Manual test: submit valid, invalid, duplicate slug

**Trigger skill**: `nextjs-frontend`

---

### Task 2.5: Detail / Edit page + Delete dialog ⬜
**Estimate**: 1.5h
**Deliverable**: `/admin/products/[id]` load existing data, edit save thành công; delete có confirm dialog

**Steps**:
1. `src/app/(admin)/products/[id]/page.tsx`:
   - Server fetch `getProduct(id)` initial → pass vào client form
   - Render `<ProductForm mode="edit" initialData={...} />`
2. Update `product-form.tsx`:
   - Branch theo mode: edit dùng useUpdateProduct, PATCH chỉ dirty fields qua `getValues()` + `formState.dirtyFields`
3. `src/app/(admin)/products/_components/delete-confirm-dialog.tsx`:
   - shadcn Dialog
   - useDeleteProduct
   - Onsuccess: toast với undo button (5s); undo gọi restore
4. Add "Delete" button trong edit page header
5. Manual test: edit + save, delete + undo

**Trigger skill**: `nextjs-frontend`

---

### Task 2.6: FE unit tests + E2E ⬜
**Estimate**: 1.5h
**Deliverable**: `npm test` (Vitest) pass; `npm run test:e2e` (Playwright) 1 spec pass

**Steps**:
1. Setup Vitest config nếu chưa có (`vitest.config.ts`) + Playwright config
2. `src/lib/schemas/__tests__/product.test.ts`:
   - parse valid input → success
   - parse invalid sku_root → fail với message đúng
   - default values khi field missing
3. `src/lib/hooks/__tests__/use-products.test.ts` với MSW handlers:
   - useProducts trả data list
   - useCreateProduct invalidate cache
4. `e2e/products.spec.ts` (Playwright):
   - login → vào /admin/products → click New → fill form → save → assert toast + new row → click row → edit name → save → delete → confirm → assert removed

**Trigger skill**: `test-generator`

---

## Phase 3: Polish

### Task 3.1: Manual QA + perf check ⬜
**Estimate**: 0.5h

**Checklist**:
- [ ] Tạo 5 product trong < 5 phút (manual UAT goal)
- [ ] Happy path từ login → list → create → edit → delete → undo
- [ ] Validation error inline hiển thị đúng (slug duplicate, sku_root invalid)
- [ ] Permission 401 khi gọi API không auth
- [ ] Responsive: form usable trên width 768px (tablet)
- [ ] Tiếng Việt có dấu trong name + description hiển thị + lưu đúng
- [ ] Audit log entry sau mỗi mutation (kiểm qua Django admin `/admin/core/auditlog/`)
- [ ] Seed 1000 Product (qua factory + management command), đo p95 list endpoint < 500ms

---

### Task 3.2: Code review qua skill ⬜
**Estimate**: 0.5h
**Deliverable**: Không có 🔴 finding, các 🟠 hoặc 🟡 được resolve hoặc ghi vào backlog

**Steps**:
1. Trigger skill `code-review` trên diff branch
2. Review findings theo severity
3. Fix 🔴, ghi 🟠/🟡 vào `docs/features/01-product-crud/CHANGELOG.md`

**Trigger skill**: `code-review`

---

### Task 3.3: Documentation + commit ⬜
**Estimate**: 0.25h

**Steps**:
1. Create `docs/features/01-product-crud/CHANGELOG.md` với date + summary
2. Update `docs/README.md` index (nếu cần)
3. Run final checks: `python manage.py check`, `pytest`, `npm run typecheck`, `npm run build`, `npm test`
4. Commit Conventional Commits: `feat(catalog): add Product CRUD (BE + FE)`

---

## Notes

- **`sku_root` không phải BR-002 SKU** (BR-002 dành cho variant SKU). `sku_root` chỉ là mã gốc dùng làm prefix `[PROD6]` khi build variant SKU sau.
- **RBAC TODO**: viewset hiện chỉ có `IsAuthenticated`. Khi feature `accounts` ready, replace bằng role-based permission. Comment `# TODO(accounts): ...` rõ ràng trong viewset.
- **Slug i18n**: tận dụng `python-slugify` (đã có trong deps). FE dùng implementation đơn giản (không slugify unicode → BE re-slug nếu cần).
- **Concurrent test** (Task 1.5) cần `--reuse-db` hoặc rollback isolation; xem pytest-django docs nếu flaky.

## Blockers / Open questions

- [ ] **OQ-1**: Cần seed dữ liệu test (1000 Product) cho Task 3.1 perf check. Nên viết management command `seed_products` hay chỉ dùng factory ad-hoc qua shell? → đề xuất management command, ~30 phút thêm.
- [ ] **OQ-2**: Login flow chưa có (feature `accounts` chưa làm). Hiện tại test API qua `createsuperuser` + `simplejwt` `/api/v1/auth/token/` endpoint. Vậy có cần feature `accounts/login UI` trước feature này không, hay tạm dùng curl + Django Admin để login? → đề xuất tạm Django Admin login + cookie session bridge, defer login UI.

---

*Created by skill: `ba-spec` | Date: 2026-05-26*
