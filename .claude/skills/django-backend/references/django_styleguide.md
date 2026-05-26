# Django Styleguide (tóm tắt HackSoft)

Tham khảo: https://github.com/HackSoftware/Django-Styleguide

## Layers

1. **Models** — data + simple validation (clean()) + constraints
2. **Selectors** — read queries (functions, không method)
3. **Services** — write operations (transactions, side effects, business rules)
4. **APIs (Views)** — DRF ViewSet/APIView, thin
5. **Serializers** — input validation + output formatting, không có business logic
6. **Tasks** — Celery async work
7. **Tests** — pytest + factory_boy

## Services rules

```python
# Bad: service trả ID không
def variant_create(...) -> str:
    return variant.id

# Good: trả model instance
def variant_create(...) -> Variant:
    return variant

# Good: keyword-only arguments
def variant_create(*, user, product_id, axes, base_price, **kwargs) -> Variant:
    ...

# Bad: hide side effect
def variant_create(...) -> Variant:
    variant = ...
    push_to_all_channels(variant)  # ← hidden!
    return variant

# Good: explicit side effects
def variant_create(*, ..., push_to_channels: bool = False) -> Variant:
    variant = ...
    if push_to_channels:
        push_variant_to_channels.delay(variant.id)
    return variant
```

## Selectors rules

```python
# selectors/variant.py

def variant_list(*, user, filters=None) -> QuerySet[Variant]:
    """Return variants visible to user, with permissions filtering."""
    qs = Variant.objects.select_related('product', 'material', 'design_file')
    
    if not user.has_perm('variant.cost_read'):
        qs = qs.defer('cost_price')
    
    if not user.is_super_admin:
        qs = qs.filter(product__owner_team=user.team)
    
    return qs

def variant_get(*, id, user) -> Variant:
    qs = variant_list(user=user)
    try:
        return qs.get(id=id)
    except Variant.DoesNotExist:
        raise NotFound('Variant not found')
```

## API design conventions

- **Versioned URLs**: `/api/v1/...`
- **Plural resource names**: `/products/` not `/product/`
- **Custom action lowercase + underscores**: `/variants/{id}/publish_to_channel/` not `/publishToChannel/`
- **Filtering qua query params**: `?status=active&material=PLA`
- **Pagination**: cursor-based cho list lớn, page-based cho admin
- **Errors trả về standard format**:

```json
{
  "error_code": "LICENSE_BLOCKS_COMMERCIAL",
  "message": "Design file license does not allow commercial use",
  "details": {
    "design_file_id": "uuid",
    "license_type": "cc_by_nc"
  }
}
```

## Naming conventions

| Type | Convention | Example |
|---|---|---|
| Model | PascalCase, singular | `Variant`, `DesignFile` |
| App | snake_case, plural noun | `apps.skus`, `apps.design_files` |
| Service function | `{entity}_{action}` | `variant_create`, `channel_publish_variant` |
| Selector function | `{entity}_{action}` | `variant_list`, `variant_get` |
| Task | verb_object | `push_variant_to_shopee` |
| URL name | `{entity}-{action}` | `variant-list`, `variant-publish-to-channel` |
| DB table | snake_case, plural | `variants`, `design_files` |
| Constants | UPPER_SNAKE | `MAX_VARIANT_AXES = 5` |

## Testing conventions

```python
# tests/test_services.py
import pytest
from apps.skus.services import variant_create
from apps.skus.exceptions import LicenseCommercialBlockError

@pytest.mark.django_db
class TestVariantCreate:
    def test_creates_with_valid_data(self, user_catalog_manager, product, license_cc0_file):
        variant = variant_create(
            user=user_catalog_manager,
            product_id=product.id,
            axes={'material_color': 'red'},
            base_price=100000,
            design_file_id=license_cc0_file.id,
        )
        assert variant.sku.startswith('FIG-')
        assert variant.status == 'draft'
    
    def test_blocks_when_license_nc(self, user_catalog_manager, product, license_nc_file):
        with pytest.raises(LicenseCommercialBlockError):
            variant_create(
                user=user_catalog_manager,
                product_id=product.id,
                axes={},
                base_price=100000,
                design_file_id=license_nc_file.id,
            )
```

## Common code smells to avoid

| Smell | Fix |
|---|---|
| Fat model với 500 dòng method | Move to services/selectors |
| Fat view với try/except + business logic | Extract to service |
| ModelSerializer dùng cho cả input/output | Tách 2 serializers riêng |
| Direct `Model.objects.filter()` trong view | Qua selector |
| Mixing reads + writes trong 1 function | Tách selector vs service |
| `def create(self, validated_data)` trong serializer chứa logic | Move to service |
| Hardcoded role check `if user.role == 'admin'` | Use permission system |
| Loop tạo nhiều object | Use `bulk_create` |
| Loop trigger N+1 query | Use `prefetch_related` |
| String concat URL | Use `reverse()` |

## Settings split

```python
# config/settings/base.py    - shared
# config/settings/dev.py     - DEBUG=True, console email, sqlite or local pg
# config/settings/test.py    - pytest, in-memory cache, CELERY_TASK_ALWAYS_EAGER=True
# config/settings/staging.py - production-like, real DB, real Celery
# config/settings/prod.py    - sentry, secret manager, strict
```

## Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    "django>=5.0,<5.2",
    "djangorestframework>=3.15",
    "django-filter",
    "django-environ",
    "drf-spectacular",
    "django-guardian",
    "celery[redis]>=5.3",
    "psycopg[binary]>=3.1",
    "Pillow",
    "boto3",         # S3/MinIO
    "requests",
    "redis>=5.0",
    "django-cors-headers",
    "django-storages[s3]",
    "cryptography",  # token encryption
    "qrcode",
    "python-barcode",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-django",
    "pytest-cov",
    "pytest-xdist",
    "factory-boy",
    "faker",
    "ruff",
    "mypy",
    "django-stubs",
    "djangorestframework-stubs",
    "ipython",
    "django-debug-toolbar",
]
```
