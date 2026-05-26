# Coding Conventions

## Git

### Branch naming

```
main                          ← Production
develop                       ← Integration (optional, depends on workflow)
feat/NN-feature-name          ← Feature branch (NN = feature folder number)
fix/NN-short-description      ← Bug fix
hotfix/short-description      ← Production emergency
chore/short-description       ← Maintenance (deps, configs)
docs/short-description        ← Docs only
```

### Commit message — Conventional Commits

```
<type>(<scope>): <subject>

<body (optional)>

<footer (optional)>
```

**Types**:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `style` — formatting (no logic change)
- `refactor` — refactor (no behavior change)
- `test` — add/update tests
- `chore` — maintenance (deps, configs)
- `perf` — performance improvement
- `ci` — CI/CD changes
- `build` — build system changes

**Scope** (optional but recommended): name of the Django app or FE module:
- BE: `catalog`, `skus`, `design_files`, `materials`, `channels`, `accounts`, `core`, ...
- FE: `auth`, `products`, `variants`, `pos`, `ui`, ...

**Examples**:

```
feat(catalog): add product CRUD endpoints

Implement create, list, retrieve, update, soft-delete for Product.
Includes:
- Service layer (services/product.py)
- ViewSet with permission_classes
- Input/Output serializers
- Migration 0002

Closes #12

---

fix(skus): handle SKU sequence gap

When variant 02 is deleted, gen should return 02 instead of 04.

---

docs(architecture): update tech stack rationale

---

chore(deps): bump djangorestframework 3.14 → 3.15
```

### Commit size

- 1 commit = 1 logical change
- Mỗi commit phải pass test + lint
- Không commit "WIP" lên main / develop
- Squash khi merge PR (cleaner history)

### PR title = commit message format

## Python (Backend)

### Code style

- **Indentation**: 4 spaces (PEP 8)
- **Line length**: 100 chars max
- **Quote style**: double quotes (`"..."`) cho strings, single quotes cho dict keys/short literals OK
- **Import order**: stdlib → 3rd party → 1st party → relative (isort)
- **Type hints**: bắt buộc cho public function signatures
- **Docstring**: Google style, bắt buộc cho service functions

```python
# Good
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.catalog.models import Product
from apps.skus.models import Variant
from apps.skus.exceptions import LicenseCommercialBlockError

if TYPE_CHECKING:
    from apps.accounts.models import User


@transaction.atomic
def variant_create(
    *,
    user: User,
    product_id: str,
    axes: dict,
    base_price: Decimal,
    design_file_id: str | None = None,
    status: str = "draft",
) -> Variant:
    """Create a variant with auto-generated SKU.

    Args:
        user: Actor performing the action (for audit log).
        product_id: UUID of parent product.
        axes: Dict containing variant axes (material_id, color, size, ...).
        base_price: Selling price in VND.
        design_file_id: Optional UUID of attached design file.
        status: Initial status, defaults to 'draft'.

    Returns:
        Created Variant instance.

    Raises:
        LicenseCommercialBlockError: If status=='active' and design_file
            does not allow commercial use (BR-003).
    """
    ...
```

### Naming

| Item | Convention | Example |
|---|---|---|
| Variable, function | `snake_case` | `variant_create`, `product_list` |
| Class | `PascalCase` | `Variant`, `ShopeeConnector` |
| Constant | `UPPER_SNAKE` | `MAX_VARIANTS_PER_PRODUCT = 100` |
| Module | `snake_case.py` | `variant_service.py` |
| Private | `_leading_underscore` | `_compute_sku_base()` |
| App | `snake_case`, plural noun | `apps/skus`, `apps/design_files` |
| Service function | `{entity}_{action}` | `variant_create`, `channel_publish_variant` |
| Selector function | `{entity}_{action}` | `variant_list`, `variant_get` |
| URL name | `{entity}-{action}` | `variant-list`, `variant-publish-to-channel` |
| DB table | `{app}_{plural_lowercase}` | `skus_variants` |

### Forbidden

- ❌ `from x import *`
- ❌ `except:` hoặc `except Exception:` rộng → catch specific
- ❌ `print()` trong production code → dùng `logger`
- ❌ Hardcoded SQL string (`.raw()`) với f-string user input → parameterized
- ❌ Magic numbers → constants
- ❌ Files > 200 dòng → split module

### Tools

```bash
ruff check .       # Lint
ruff format .      # Format (replaces black + isort)
mypy apps/         # Type check
pytest             # Test
```

## TypeScript (Frontend)

### Code style

- **Indentation**: 2 spaces
- **Line length**: 100 chars
- **Quote style**: single quotes (`'...'`) trừ JSX attributes (double)
- **Semicolons**: required
- **Trailing commas**: required (Prettier default)

### Naming

| Item | Convention | Example |
|---|---|---|
| Variable, function | `camelCase` | `getProducts`, `useVariants` |
| Constant (module-level) | `UPPER_SNAKE` | `MAX_FILE_SIZE_MB = 500` |
| Component | `PascalCase` | `VariantCreateForm`, `ProductList` |
| Type / Interface | `PascalCase` | `type Product`, `interface VariantProps` |
| Hook | `use` prefix + `camelCase` | `useVariants`, `useAuth` |
| File (component) | `kebab-case.tsx` | `variant-create-form.tsx` |
| File (utility) | `kebab-case.ts` | `format-currency.ts` |
| Folder | `kebab-case` | `design-files/`, `variant-matrix/` |
| API client function | `{resource}Api.{action}` | `variantsApi.list`, `productsApi.create` |
| React Query keys | `{resource}Keys.*` | `variantKeys.list({...})` |

### TypeScript rules

- ✅ Strict mode enabled
- ❌ `any` cấm dùng → `unknown` + narrow, hoặc define proper type
- ✅ Type exports từ `lib/types/` để share giữa components
- ✅ Generate types từ DRF OpenAPI spec qua `openapi-typescript`

### Component conventions

- ✅ Server Component **default**, `'use client'` chỉ khi cần
- ✅ Co-locate component types với component (interface ngay trên function)
- ✅ Props destructuring trong signature, không trong body
- ✅ Component export default (cho lazy import) hoặc named export (cho composition)

```tsx
// Good
interface VariantCardProps {
  variant: Variant;
  onEdit?: (id: string) => void;
}

export function VariantCard({ variant, onEdit }: VariantCardProps) {
  return (...);
}
```

### Forbidden

- ❌ `any` type
- ❌ Inline `style={{}}` (dùng Tailwind class)
- ❌ `dangerouslySetInnerHTML` với user input
- ❌ `useEffect` để fetch (dùng React Query)
- ❌ `useState` cho server data (dùng React Query cache)
- ❌ Files > 200 dòng
- ❌ `console.log` trong production (chỉ `console.error` cho real errors)

### Tools

```bash
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run format      # Prettier
npm test            # Vitest
npm run test:e2e    # Playwright
```

## Comments

### Khi nào viết comment

- ✅ Giải thích **TẠI SAO** (intent, business rule reference)
- ✅ Workaround cho bug external (link issue)
- ✅ Performance trade-off
- ✅ TODO/FIXME với ticket reference

### Khi nào KHÔNG viết

- ❌ Lặp lại tên function/class (`# get the user → def get_user():`)
- ❌ Outdated (better delete than wrong)
- ❌ Commented-out code (delete it, Git có history)

### Examples

```python
# Good — explains WHY
# Shopee Open Platform giới hạn 50 variants/stock call
# nên phải batch
for batch in _chunked(items, 50):
    ...

# BR-004: Tiki chỉ support tối đa 2 option attributes
# Nếu product có > 2 axes active → block trước khi push
if len(active_axes) > 2:
    raise TikiOptionAttributesExceededError(...)

# Bad — restates code
# Loop through items
for item in items:
    ...
```

```tsx
// Good — references business decision
// POS phải work offline-first: lưu vào IndexedDB trước,
// trigger background sync khi online (xem docs/architecture/full-spec.md §POS)
await createOrderOffline(items);

// Bad
// Create order
await createOrderOffline(items);
```

### Language

- **Code identifiers** (variable, function, class, file): English
- **Comments**: Tiếng Việt OK cho business logic phức tạp, English cho technical infrastructure
- **Docstrings**: English (PyPI compatibility, IDE hover)
- **Error messages user-facing**: Tiếng Việt qua i18n
- **Error messages developer-facing** (logs, exceptions): English

## File organization

### Maximum size

- Code file: 200 lines (split khi vượt)
- SKILL.md: 500 lines (skill-creator guideline)
- Test file: 300 lines (split theo class/function group)

### When to split

```python
# apps/skus/models.py becomes too long → split:
apps/skus/models/
    __init__.py       # re-exports
    variant.py
    sku_code.py
```

```tsx
// product-form.tsx becomes too long → split:
components/product/product-form/
    index.tsx          # main component
    basic-info-fields.tsx
    pricing-fields.tsx
    attributes-fields.tsx
    use-product-form.ts # custom hook
```

## Testing

### Naming

```python
# Format: test_<what>_<expected>_when_<condition>
def test_creates_variant_when_valid_data(self):
    ...

def test_blocks_publish_when_license_is_nc(self):
    ...

def test_returns_403_when_role_lacks_permission(self):
    ...
```

### Structure

```python
@pytest.mark.django_db
class TestVariantCreate:
    """Tests for variant_create service."""

    def test_creates_with_valid_data(self):
        # Arrange
        product = ProductFactory()
        user = UserFactory()

        # Act
        variant = variant_create(
            user=user, product_id=product.id, axes={}, base_price=Decimal('100000'),
        )

        # Assert
        assert variant.status == 'draft'
        assert variant.created_by == user
```

### Coverage targets

| Layer | Target |
|---|---|
| Services | 90%+ |
| Selectors | 80%+ |
| Models (custom logic) | 80%+ |
| Views | 70%+ |
| Celery tasks | 80%+ |
| Connectors (mocked) | 70%+ |
| FE components | 70%+ |
| FE hooks | 80%+ |
| E2E critical paths | 100% |
