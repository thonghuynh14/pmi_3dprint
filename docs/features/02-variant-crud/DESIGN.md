# DESIGN — Variant CRUD (02-variant-crud)

## Kiến trúc tổng quan

```
FE (Next.js)                          BE (Django + DRF)
─────────────                         ──────────────────
/admin/products/<id>/variants         apps/skus/
  ├─ list page                          ├─ models.py        Variant
  ├─ /new   single form                 ├─ services/        variant_create, variant_bulk_create_matrix, ...
  ├─ /new-matrix  matrix UI             ├─ selectors/       get_variant, list_variants
  └─ /<vid> edit                        ├─ serializers/     Input / Matrix / Output / List
                                        ├─ views/           ViewSet + nested bulk action
                                        ├─ exceptions.py    Domain errors
                                        └─ migrations/      0001_initial + RunSQL indexes
```

App mới: **`apps.skus`** (theo convention `apps/<plural>`). Variant là entity duy nhất trong app này v1.

---

## Backend

### Module breakdown

```
apps/skus/
├─ __init__.py
├─ apps.py
├─ admin.py                 # ModelAdmin với get_queryset all_objects + bulk actions
├─ urls.py                  # Router /variants/ + nested bulk-matrix
├─ models.py                # Variant
├─ exceptions.py            # Domain exceptions (APIException subclasses)
├─ services/
│   ├─ __init__.py
│   └─ variants.py          # variant_create, variant_update, variant_soft_delete,
│                           # variant_restore, variant_bulk_create_matrix
├─ selectors/
│   ├─ __init__.py
│   └─ variants.py          # get_variant, list_variants
├─ serializers/
│   ├─ __init__.py
│   └─ variants.py          # VariantInputSerializer, VariantMatrixInputSerializer,
│                           # VariantUpdateSerializer, VariantOutputSerializer,
│                           # VariantListItemSerializer
├─ views/
│   ├─ __init__.py
│   └─ variants.py          # VariantViewSet + matrix endpoint
├─ migrations/
│   └─ 0001_initial.py      # CreateModel + RunSQL indexes
└─ tests/
    ├─ __init__.py
    ├─ factories.py
    ├─ test_models.py
    ├─ test_services.py     # incl. race condition test
    └─ test_api.py
```

### Model `Variant`

Extends `BaseModel` = `UUIDModel + TimestampedModel + SoftDeleteModel + AuditedModel` (đã có).

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `id` | UUID | PK | from UUIDModel |
| `product` | FK→catalog.Product | `PROTECT`, db_index | Variant chết khi Product cố hard delete; Product soft delete không cascade |
| `sku` | CharField(24) | partial unique `LOWER(sku) WHERE deleted_at IS NULL` | BR-001 |
| `sequence_no` | PositiveIntegerField | partial unique `(product_id, sequence_no) WHERE deleted_at IS NULL`, CHECK ≥1 | Per-product counter |
| `material_name` | CharField(64) | non-empty | "Polylactic Acid" |
| `material_code3` | CharField(4) | regex `^[A-Z0-9]{2,4}$` | "PLA" |
| `color_name` | CharField(64) | non-empty | "Red" |
| `color_code3` | CharField(4) | regex `^[A-Z0-9]{2,4}$` | "RED" |
| `size_preset` | CharField(8) | regex `^[A-Za-z0-9]{1,8}$` | "M" hoặc "12cm" |
| `name` | CharField(200) | auto-gen | "Dragon Figure - PLA Red M" |
| `base_price` | DecimalField(12,2) | CHECK ≥0 | VND |
| `cost_price` | DecimalField(12,2) | nullable, CHECK isnull OR ≥0 | VND |
| `status` | CharField(16) | choices: draft/active/archived | TextChoices |
| `attributes` | JSONField | default={} | Extras (vd `{"finish":"matte"}`) |
| `created_at/updated_at` | DateTime | from TimestampedModel | |
| `deleted_at` | DateTime | nullable, from SoftDeleteModel | |
| `created_by/updated_by` | FK→User | from AuditedModel | |

**Combo unique** (per-product, case-insensitive): partial unique index `(product_id, LOWER(material_code3), LOWER(color_code3), LOWER(size_preset)) WHERE deleted_at IS NULL`.

### Indexes (migration 0001 RunSQL)

```sql
-- BR-001 SKU unique case-insensitive (active records only)
CREATE UNIQUE INDEX skus_variants_sku_unique_active
  ON skus_variants (LOWER(sku)) WHERE deleted_at IS NULL;

-- Combo unique per product
CREATE UNIQUE INDEX skus_variants_combo_unique_active
  ON skus_variants (product_id, LOWER(material_code3), LOWER(color_code3), LOWER(size_preset))
  WHERE deleted_at IS NULL;

-- Sequence unique per product
CREATE UNIQUE INDEX skus_variants_seq_unique_active
  ON skus_variants (product_id, sequence_no) WHERE deleted_at IS NULL;

-- Search indexes (trigram)
CREATE INDEX skus_variants_name_trgm
  ON skus_variants USING gin (name gin_trgm_ops);
CREATE INDEX skus_variants_sku_trgm
  ON skus_variants USING gin (sku gin_trgm_ops);

-- JSON attributes
CREATE INDEX skus_variants_attributes_gin
  ON skus_variants USING gin (attributes jsonb_path_ops);
```

Migration depends on `catalog.0001_initial` (Product) + `core.0002_postgres_extensions`.

### Helpers (`apps/skus/utils.py`)

```python
SKU_LEN_MIN = 12
SKU_LEN_MAX = 24
MAX_BATCH = 100

def compute_sku(sku_root: str, material_code3: str, color_code3: str,
                size_preset: str, sequence_no: int) -> str:
    return f"{sku_root}-{material_code3}-{color_code3}-{size_preset}-{sequence_no:02d}"

def validate_sku_length(sku: str) -> None:
    if not (SKU_LEN_MIN <= len(sku) <= SKU_LEN_MAX):
        raise SkuLengthInvalidError(sku=sku, length=len(sku))

def compute_variant_name(product_name: str, material_name: str,
                         color_name: str, size_preset: str) -> str:
    return f"{product_name} - {material_name} {color_name} {size_preset}"
```

### Exceptions (`apps/skus/exceptions.py`)

| Exception | HTTP | error_code |
|---|---|---|
| `VariantNotFoundError` | 404 | `VARIANT_NOT_FOUND` |
| `DuplicateSkuError` | 409 | `DUPLICATE_SKU` |
| `DuplicateVariantComboError` | 409 | `DUPLICATE_VARIANT_COMBO` |
| `DuplicateInMatrixInputError` | 400 | `DUPLICATE_IN_MATRIX_INPUT` |
| `BatchTooLargeError` | 400 | `VARIANT_BATCH_TOO_LARGE` |
| `EmptyMatrixError` | 400 | `EMPTY_MATRIX` |
| `ProductArchivedError` | 400 | `PRODUCT_ARCHIVED` |
| `SkuLengthInvalidError` | 400 | `SKU_LENGTH_INVALID` |
| `VariantFieldImmutableError` | 400 | `VARIANT_FIELD_IMMUTABLE` |
| `RestoreConflictError` | 409 | `RESTORE_CONFLICT` (reuse pattern Product nếu combo trùng khi restore) |

Pattern y hệt `apps/catalog/exceptions.py` (extend `APIException`).

### Services (signature)

```python
# apps/skus/services/variants.py
from decimal import Decimal

@transaction.atomic
def variant_create(*, user, product_id, material_name, material_code3,
                   color_name, color_code3, size_preset, base_price,
                   cost_price=None, status="draft", attributes=None) -> Variant: ...

@transaction.atomic
def variant_update(*, user, variant_id, base_price=None, cost_price=None,
                   status=None, attributes=None) -> Variant: ...
# Chỉ accept các field cho phép. Field khác (material_*, color_*, size_*, sku) → reject 400.

@transaction.atomic
def variant_soft_delete(*, user, variant_id) -> Variant: ...

@transaction.atomic
def variant_restore(*, user, variant_id) -> Variant: ...

@transaction.atomic
def variant_bulk_create_matrix(*, user, product_id,
                               materials: list[dict], colors: list[dict],
                               sizes: list[str], base_price: Decimal,
                               cost_price: Decimal | None = None,
                               status: str = "draft") -> list[Variant]:
    """
    materials: [{"name": "PLA", "code3": "PLA"}, ...]
    colors: [{"name": "Red", "code3": "RED"}, ...]
    sizes: ["S", "M", "L"]
    """
    # 1. Validate total = N*M*P ∈ [1, 100]
    # 2. Validate no duplicate code3 trong materials, colors; no duplicate trong sizes (case-insensitive)
    # 3. Product = select_for_update().get(id=product_id), check active + not deleted
    # 4. Lấy last_seq = aggregate Max(sequence_no) trên product này
    # 5. Loop tổ hợp: gen SKU, gen name; collect vào list (chưa save)
    # 6. Pre-check combo trùng với DB (filter case-insensitive WHERE deleted_at IS NULL)
    # 7. bulk_create(list)
    # 8. Catch IntegrityError → _raise_for_integrity (mapping unique violation)
    # 9. Tạo AuditLog cho mỗi variant
    # 10. Return list
```

**Critical implementation detail — race protection**:
- `Product.objects.select_for_update().get(...)` ở dòng đầu → lock row Product cho cả transaction
- 2 transaction concurrent cùng product sẽ serial hoá (transaction sau đợi transaction trước commit)
- → sequence_no luôn monotonic, không collision

### Selectors

```python
# apps/skus/selectors/variants.py
def get_variant(*, variant_id, include_deleted=False) -> Variant:
    """Catch (DoesNotExist, ValueError, ValidationError) → VariantNotFoundError."""

def list_variants(*, product_id=None, search="", status=None,
                  show_archived=False, ordering="sequence_no") -> QuerySet[Variant]:
    """Apply filters; .select_related('product') để tránh N+1; nếu show_archived dùng all_objects manager."""
```

### Serializers

```python
# apps/skus/serializers/variants.py

class VariantInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    material_name = serializers.CharField(max_length=64, min_length=1)
    material_code3 = serializers.RegexField(regex=r"^[A-Z0-9]{2,4}$", max_length=4)
    color_name = serializers.CharField(max_length=64, min_length=1)
    color_code3 = serializers.RegexField(regex=r"^[A-Z0-9]{2,4}$", max_length=4)
    size_preset = serializers.RegexField(regex=r"^[A-Za-z0-9]{1,8}$", max_length=8)
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[("draft","draft"),("active","active"),("archived","archived")], default="draft")
    attributes = serializers.JSONField(required=False, default=dict)

    def validate_material_code3(self, v): return v.upper()
    def validate_color_code3(self, v): return v.upper()
    # size_preset không upper (vì có thể "12cm")

class VariantMatrixInputSerializer(serializers.Serializer):
    class AxisEntry(serializers.Serializer):
        name = serializers.CharField(max_length=64, min_length=1)
        code3 = serializers.RegexField(regex=r"^[A-Z0-9]{2,4}$", max_length=4)

        def validate_code3(self, v): return v.upper()

    materials = AxisEntry(many=True, min_length=1)
    colors = AxisEntry(many=True, min_length=1)
    sizes = serializers.ListField(
        child=serializers.RegexField(regex=r"^[A-Za-z0-9]{1,8}$", max_length=8),
        min_length=1,
    )
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[("draft","draft"),("active","active"),("archived","archived")], default="draft")

    def validate(self, data):
        total = len(data["materials"]) * len(data["colors"]) * len(data["sizes"])
        if total > 100:
            raise BatchTooLargeError(max=100, requested=total)
        # duplicate code3 / size detect ở service (clearer error)
        return data

class VariantUpdateSerializer(serializers.Serializer):
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[...], required=False)
    attributes = serializers.JSONField(required=False)
    # KHÔNG accept material_*/color_*/size_*/sku — DRF tự ignore unknown field
    # Nhưng nếu user gửi field này, mong muốn trả 400 "field immutable" → custom validate

class VariantOutputSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    class Meta:
        model = Variant
        fields = ["id","sku","sequence_no","name","product_id","product_name",
                  "material_name","material_code3","color_name","color_code3","size_preset",
                  "base_price","cost_price","status","attributes",
                  "created_at","updated_at","deleted_at"]

class VariantListItemSerializer(serializers.ModelSerializer):
    """Narrow fields cho list view."""
    class Meta:
        model = Variant
        fields = ["id","sku","name","material_code3","color_code3","size_preset",
                  "base_price","status","sequence_no","deleted_at"]
```

### Views & URLs

```python
# apps/skus/views/variants.py
class VariantViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]  # RBAC defer
    http_method_names = ["get","post","patch","delete","head","options"]  # no PUT (full replace risk)

    def list(self, request): ...                       # GET /variants/?product=&search=&status=&show_archived=
    def retrieve(self, request, pk): ...               # GET /variants/<id>/
    def create(self, request): ...                     # POST /variants/  (single)
    def partial_update(self, request, pk): ...         # PATCH /variants/<id>/
    def destroy(self, request, pk): ...                # DELETE /variants/<id>/  (soft)
    @action(detail=True, methods=["post"])
    def restore(self, request, pk): ...                # POST /variants/<id>/restore/

# Matrix endpoint nested dưới catalog product để URL có ngữ cảnh
class ProductVariantMatrixView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, product_id):                # POST /catalog/products/<id>/variants/bulk-matrix/
        serializer = VariantMatrixInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variants = variant_bulk_create_matrix(user=request.user, product_id=product_id, **serializer.validated_data)
        return Response({"count": len(variants), "created": VariantOutputSerializer(variants, many=True).data}, status=201)
```

URL mount:
```python
# apps/skus/urls.py
router = SimpleRouter()
router.register(r"variants", VariantViewSet, basename="variants")
urlpatterns = [path("", include(router.urls))]

# config/urls.py — add:
path("api/v1/skus/", include("apps.skus.urls")),
path("api/v1/catalog/products/<uuid:product_id>/variants/bulk-matrix/",
     ProductVariantMatrixView.as_view(), name="product-variants-bulk-matrix"),
```

Final endpoints:
- `GET    /api/v1/skus/variants/`
- `POST   /api/v1/skus/variants/`
- `GET    /api/v1/skus/variants/<id>/`
- `PATCH  /api/v1/skus/variants/<id>/`
- `DELETE /api/v1/skus/variants/<id>/`
- `POST   /api/v1/skus/variants/<id>/restore/`
- `POST   /api/v1/catalog/products/<product_id>/variants/bulk-matrix/`

### Admin

`apps/skus/admin.py` — copy pattern `apps/catalog/admin.py`:
- list_display: `sku`, `name`, `product`, `status`, `base_price`, `sequence_no`, `deleted_at`
- list_filter: `status`, `deleted_at`, `material_code3`
- search_fields: `sku`, `name`, `product__name`
- readonly_fields: `sku`, `sequence_no`, `name`, `created_*`, `updated_*`, `deleted_at`
- Bulk actions: soft_delete, restore

### Settings change

`config/settings/base.py`:
```python
LOCAL_APPS = ["apps.core", "apps.catalog", "apps.skus"]
```

---

## Frontend

### Routes

```
/admin/products/[id]/variants                    # list + actions
/admin/products/[id]/variants/new                # single form
/admin/products/[id]/variants/new-matrix         # matrix form
/admin/products/[id]/variants/[vid]              # edit
```

Tất cả nested dưới product để có ngữ cảnh; flat `/admin/variants` defer.

### Component breakdown

```
src/app/admin/products/[id]/variants/
├─ page.tsx                                        # Server shell, renders <VariantsListClient productId={id} />
├─ _components/
│   ├─ variants-list-client.tsx                    # TanStack Table + filters
│   ├─ variants-toolbar.tsx                        # search + status filter + show_archived toggle
│   ├─ columns.tsx                                 # sku, name, material/color/size, price, status, actions
│   └─ delete-confirm-dialog.tsx                   # reuse / extract chung từ products
├─ new/page.tsx                                    # /variants/new — wraps <VariantSingleForm productId={id} />
├─ new-matrix/page.tsx                             # /variants/new-matrix — wraps <VariantMatrixForm productId={id} />
└─ [vid]/
    ├─ page.tsx                                    # server shell
    └─ _components/
        └─ variant-edit-client.tsx                 # uses <VariantSingleForm mode="edit" />

src/components/variants/
├─ variant-single-form.tsx                         # RHF + zod; props: productId, mode (create|edit), defaults
├─ variant-matrix-form.tsx                         # axis chip inputs + preview table + submit
└─ variant-matrix-preview-table.tsx                # read-only N×M×P preview rows

src/lib/
├─ types/variant.ts                                # Variant, VariantInput, MatrixInput, ...
├─ schemas/variant.ts                              # productVariantInputSchema, productVariantMatrixSchema, productVariantUpdateSchema
├─ api/variants.ts                                 # axios methods
└─ hooks/use-variants.ts                           # useVariants, useVariant, useCreateVariant, useUpdateVariant,
                                                   #   useDeleteVariant, useRestoreVariant, useCreateVariantMatrix
```

### Data flow

#### List
```
VariantsListPage (server) → <VariantsListClient productId>
  └─ useVariants({ productId, search, status, show_archived })
       └─ GET /api/v1/skus/variants/?product=<id>&search=&status=&show_archived=
       └─ Render Table với columns; row actions: edit (navigate), delete (open dialog)
```

#### Single create
```
/new page → <VariantSingleForm productId mode="create">
  └─ RHF + zod (productVariantInputSchema)
  └─ useCreateVariant().mutate(payload)
       └─ POST /api/v1/skus/variants/  body={product_id, material_*, color_*, size_preset, base_price, ...}
       └─ onSuccess: toast + invalidate ['variants', productId, ...] + router.push to list
```

#### Matrix create
```
/new-matrix page → <VariantMatrixForm productId>
  ├─ AxisChipInput cho materials (name + code3)
  ├─ AxisChipInput cho colors (name + code3)
  ├─ AxisChipInput cho sizes (string only)
  ├─ Pricing inputs (base_price, cost_price, status)
  ├─ Real-time count: "Tạo {N*M*P} variants"
  ├─ Button "Preview" → <VariantMatrixPreviewTable> render rows
  │   - Mỗi row: name (computed), SKU (placeholder "auto-{n+1}"), material/color/size
  ├─ Confirm "Tạo tất cả" → useCreateVariantMatrix().mutate(payload)
  │   └─ POST /api/v1/catalog/products/<id>/variants/bulk-matrix/
  └─ onSuccess: toast "Đã tạo {count} variants" + invalidate + router.push list
```

#### Edit
```
/[vid] page → <VariantEditClient variantId>
  ├─ useVariant(variantId) → prefill form
  └─ <VariantSingleForm mode="edit" defaults>
      ├─ Disable: material_*/color_*/size_preset/sku (visible nhưng readonly)
      └─ Editable: base_price/cost_price/status/attributes
      └─ useUpdateVariant(variantId).mutate(payload)
           └─ PATCH /api/v1/skus/variants/<id>/
```

### Zod schemas

```typescript
// src/lib/schemas/variant.ts
export const code3Schema = z.string().regex(/^[A-Z0-9]{2,4}$/, "Code 3 phải 2-4 chữ in hoa/số");
export const sizePresetSchema = z.string().regex(/^[A-Za-z0-9]{1,8}$/, "Size 1-8 ký tự alphanumeric");

export const variantInputSchema = z.object({
  product_id: z.string().uuid(),
  material_name: z.string().min(1).max(64),
  material_code3: code3Schema,
  color_name: z.string().min(1).max(64),
  color_code3: code3Schema,
  size_preset: sizePresetSchema,
  base_price: z.coerce.number().min(0),
  cost_price: z.coerce.number().min(0).nullable().optional(),
  status: z.enum(["draft","active","archived"]).default("draft"),
  attributes: z.record(z.unknown()).default({}),
});

export const axisEntrySchema = z.object({
  name: z.string().min(1).max(64),
  code3: code3Schema,
});

export const variantMatrixInputSchema = z.object({
  materials: z.array(axisEntrySchema).min(1).max(20),
  colors: z.array(axisEntrySchema).min(1).max(20),
  sizes: z.array(sizePresetSchema).min(1).max(20),
  base_price: z.coerce.number().min(0),
  cost_price: z.coerce.number().min(0).nullable().optional(),
  status: z.enum(["draft","active","archived"]).default("draft"),
}).refine(
  (d) => d.materials.length * d.colors.length * d.sizes.length <= 100,
  { message: "Tổng variants vượt 100 (giới hạn batch)" }
);

export const variantUpdateSchema = z.object({
  base_price: z.coerce.number().min(0).optional(),
  cost_price: z.coerce.number().min(0).nullable().optional(),
  status: z.enum(["draft","active","archived"]).optional(),
  attributes: z.record(z.unknown()).optional(),
});
```

### Modify existing files

- `src/app/admin/products/[id]/_components/product-edit-client.tsx` — thêm 1 button "Quản lý variants" trỏ `/variants`
- `src/test/msw/handlers.ts` — thêm handler cho variant endpoints
- `frontend/e2e/products.spec.ts` (hoặc tạo `variants.spec.ts`) — thêm e2e tạo product → matrix

---

## Technical decisions (chose X over Y)

| Decision | Chose | Over | Lý do |
|---|---|---|---|
| App name | `apps.skus` | `apps.variants` | Theo full-spec, SKU module bao toàn bộ variant — đặt đúng namespace tương lai |
| Material/Color FK | String denormalized | FK Material model | Material chưa có; v1 tách scope rõ ràng |
| SKU pattern | `<sku_root>-<MAT>-<COL>-<SIZE>-<NN>` | BR-002 đầy đủ với CAT3 | Category chưa có; vẫn ∈ BR-002 range 12-24 |
| Sequence | Per-product counter | Global counter | Số nhỏ trong SKU, dễ đọc; lock scope hẹp hơn |
| Race protection | `select_for_update(Product)` | Advisory lock / unique violation retry | Idiomatic Django; transaction-scoped; minimal code |
| Matrix endpoint | Nested `/catalog/products/<id>/variants/bulk-matrix/` | Overload POST /variants/ với optional matrix payload | Clear API surface; permission/filter dễ |
| Edit immutable axis | Reject 400 nếu user gửi material_* | Silent ignore | Fail loud, tránh hiểu nhầm |
| FE matrix UI v1 | Generate + preview (no per-cell edit) | Per-cell edit ngay v1 | Giảm complexity FE state; 80% case không cần edit |
| Variant `name` field | DB column auto-gen | Compose ở UI | Search được; consistency; ít tính lại |
| `on_delete=PROTECT` cho Product FK | PROTECT | CASCADE / SET_NULL | Product hard delete không tồn tại (chỉ soft); PROTECT là default an toàn nhất |
| FE route nested | `/products/<id>/variants/...` | Flat `/variants` riêng | Variant luôn có ngữ cảnh Product; URL self-documenting |

## API contracts

### POST /api/v1/skus/variants/ (single)

```json
// Request
{
  "product_id": "8e1c...",
  "material_name": "Polylactic Acid",
  "material_code3": "PLA",
  "color_name": "Red",
  "color_code3": "RED",
  "size_preset": "M",
  "base_price": "150000",
  "cost_price": "40000",
  "status": "draft",
  "attributes": {}
}

// Response 201
{
  "id": "f7a2...",
  "sku": "DRAGON-PLA-RED-M-01",
  "sequence_no": 1,
  "name": "Dragon Figure - Polylactic Acid Red M",
  "product_id": "8e1c...",
  "product_name": "Dragon Figure",
  "material_name": "Polylactic Acid", "material_code3": "PLA",
  "color_name": "Red", "color_code3": "RED",
  "size_preset": "M",
  "base_price": "150000.00", "cost_price": "40000.00",
  "status": "draft", "attributes": {},
  "created_at": "...", "updated_at": "...", "deleted_at": null
}

// Error 409
{
  "detail": "Variant đã tồn tại với material+color+size này",
  "error_code": "DUPLICATE_VARIANT_COMBO"
}
```

### POST /api/v1/catalog/products/<product_id>/variants/bulk-matrix/

```json
// Request
{
  "materials": [
    {"name": "PLA",  "code3": "PLA"},
    {"name": "PETG", "code3": "PET"}
  ],
  "colors": [
    {"name": "Red",   "code3": "RED"},
    {"name": "Blue",  "code3": "BLU"},
    {"name": "Green", "code3": "GRN"}
  ],
  "sizes": ["S", "M", "L"],
  "base_price": "150000",
  "cost_price": "40000",
  "status": "draft"
}

// Response 201
{
  "count": 18,
  "created": [
    { "id":"...", "sku":"DRAGON-PLA-RED-S-01", ... },
    { "id":"...", "sku":"DRAGON-PLA-RED-M-02", ... },
    ... 16 more
  ]
}

// Error 400
{
  "detail": "Tổng variants vượt giới hạn batch",
  "error_code": "VARIANT_BATCH_TOO_LARGE",
  "max": 100,
  "requested": 1000
}
```

### PATCH /api/v1/skus/variants/<id>/

```json
// Request
{ "base_price": "180000", "status": "active" }

// Response 200 — full Output

// Error 400 nếu user gửi field immutable
{
  "detail": "Field 'material_code3' không thể sửa sau khi tạo",
  "error_code": "VARIANT_FIELD_IMMUTABLE",
  "field": "material_code3"
}
```

### GET /api/v1/skus/variants/?product=<id>&search=&status=&show_archived=

Standard paginated list. `select_related('product')` để tránh N+1.

---

## Risks & mitigations recap (từ ANALYSIS)

| Risk | Mitigation in DESIGN |
|---|---|
| R1 race sequence_no | `select_for_update(Product)` trong service + test thread |
| R2 variant explosion | `MAX_BATCH=100` ở serializer + service; FE disable submit nếu > 100, warn nếu > 50 |
| R3 matrix UI complexity | v1 chỉ preview-then-confirm (no per-cell edit); 2 sub-component (axis input + preview table) |
| R4 SKU thiếu CAT3 | Documented v1 pattern; migration plan khi Category ra |
| R5 code3 từ string | Form 2-field (name + code3); zod validate code3 pattern |
