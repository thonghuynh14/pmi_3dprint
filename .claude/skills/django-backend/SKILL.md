---
name: django-backend
description: Sinh code Django + Django REST Framework cho dự án quản lý sản phẩm/SKU in 3D. Use this skill whenever the user mentions "Django", "DRF", "API endpoint", "viewset", "serializer", "model", "tạo CRUD", "tạo module backend", "tạo app Django", "viết view", or asks to implement any backend feature — even casually like "code BE cho tính năng X", "làm API cho ...", "thêm endpoint Y". Also triggers for Celery tasks, signals, middleware, custom managers, permissions, pagination, filtering, and marketplace connector implementations.
---

# Django Backend Generator cho dự án 3D Printing PIM

Skill này sinh code Django + DRF chuẩn cho hệ thống quản lý sản phẩm/SKU/đa kênh. Code output phải production-ready, không phải skeleton.

## Stack cố định

- **Django 5.0+** (LTS preferred)
- **Django REST Framework 3.15+**
- **PostgreSQL 16** với JSONB, ltree extension
- **Celery + Redis** cho async task
- **django-environ** cho config
- **django-filter** cho filtering
- **drf-spectacular** cho OpenAPI docs
- **django-allauth** hoặc **dj-rest-auth** cho auth
- **django-guardian** cho object-level permissions (RBAC)
- **psycopg[binary]** driver (v3)

## Cấu trúc project chuẩn

```
backend/
├── manage.py
├── pyproject.toml
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── prod.py
│   │   └── test.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── catalog/          # products, categories, attributes
│   ├── skus/             # variants, sku generation
│   ├── design_files/     # STL/GLB management
│   ├── materials/        # materials master + BOM
│   ├── printers/         # printer database
│   ├── poc/              # POC versions, costing
│   ├── ideas/            # idea pipeline
│   ├── channels/         # marketplace connectors (shopee, lazada, tiki)
│   ├── pos/              # POS app
│   ├── orders/           # unified orders
│   ├── accounts/         # user + RBAC
│   └── core/             # shared models, utils, mixins
└── tests/
```

**Mỗi Django app** tuân thủ pattern:
```
apps/{app_name}/
├── __init__.py
├── apps.py
├── admin.py
├── models/              # tách nhiều file nếu > 300 lines
│   ├── __init__.py
│   ├── product.py
│   └── variant.py
├── serializers/
├── views/               # ViewSets, APIViews
├── filters.py
├── permissions.py
├── services/            # business logic, không để trong view/serializer
├── selectors/           # query builders (Django styleguide từ HackSoft)
├── tasks.py             # Celery tasks
├── signals.py
├── managers.py          # custom managers/querysets
├── validators.py
├── exceptions.py
├── urls.py
├── migrations/
└── tests/
    ├── factories.py     # factory_boy
    ├── test_models.py
    ├── test_services.py
    ├── test_views.py
    └── test_tasks.py
```

## Nguyên tắc code

### 1. Service layer pattern (HackSoft Django Styleguide)

**ViewSet không chứa business logic.** Logic đặt trong `services/` (write) và `selectors/` (read).

```python
# ❌ BAD - logic trong view
class VariantViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = VariantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 50 dòng logic SKU generation, license check, audit log ở đây...
        return Response(...)

# ✅ GOOD - delegate cho service
class VariantViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = VariantCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = variant_create(
            user=request.user,
            **serializer.validated_data,
        )
        output = VariantDetailSerializer(variant).data
        return Response(output, status=201)
```

```python
# apps/skus/services/variant.py
from django.db import transaction
from apps.skus.models import Variant
from apps.skus.utils.sku_generator import generate_sku
from apps.design_files.services import design_file_check_license_for_commercial
from apps.core.audit import audit_log

@transaction.atomic
def variant_create(*, user, product_id, axes, base_price, design_file_id=None, **kwargs):
    """Create a variant with auto-generated SKU.
    
    Raises:
        LicenseCommercialBlockError: if design_file has CC BY-NC license
        SkuConflictError: if generated SKU collides
    """
    if design_file_id:
        design_file_check_license_for_commercial(design_file_id=design_file_id)
    
    sku = generate_sku(product_id=product_id, axes=axes)
    
    variant = Variant.objects.create(
        product_id=product_id,
        sku=sku,
        axes=axes,
        base_price=base_price,
        design_file_id=design_file_id,
        created_by=user,
        **kwargs,
    )
    
    audit_log(
        actor=user,
        action='variant.created',
        entity=variant,
        diff={'sku': sku, 'axes': axes},
    )
    return variant
```

### 2. Serializer patterns

**Tách input vs output serializers** — không reuse 1 serializer cho cả 2.

```python
class VariantCreateInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    axes = serializers.JSONField()
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    design_file_id = serializers.UUIDField(required=False, allow_null=True)
    # Không dùng ModelSerializer cho input vì:
    # 1. Tránh expose toàn bộ model fields
    # 2. Validation tách biệt rõ ràng
    # 3. Dễ test


class VariantDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    design_file = DesignFileBriefSerializer(read_only=True)
    bom_items = BomLineSerializer(source='bom.lines', many=True, read_only=True)
    
    class Meta:
        model = Variant
        fields = [
            'id', 'sku', 'product_id', 'product_name',
            'axes', 'base_price', 'status',
            'design_file', 'bom_items',
            'created_at', 'updated_at',
        ]
```

### 3. Model conventions

```python
# apps/skus/models/variant.py
import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from apps.core.models import TimestampedModel, SoftDeleteModel, AuditedModel


class Variant(TimestampedModel, SoftDeleteModel, AuditedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        OOS = 'oos', 'Out of stock'
        EOL = 'eol', 'End of life'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='variants',
    )
    sku = models.CharField(max_length=32, unique=True, db_index=True)
    barcode = models.CharField(max_length=14, blank=True, db_index=True)
    
    # Variant axes
    material = models.ForeignKey('materials.Material', on_delete=models.PROTECT, null=True)
    material_color = models.CharField(max_length=32, blank=True)
    size_preset = models.CharField(max_length=16, blank=True)
    layer_resolution_mm = models.DecimalField(max_digits=4, decimal_places=3, null=True)
    infill_percent = models.PositiveSmallIntegerField(null=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Dimensions
    weight_g = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    dimensions_mm = models.JSONField(default=dict)
    
    # Flexible attributes
    attributes = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    is_made_to_order = models.BooleanField(default=False)
    lead_time_hours = models.PositiveSmallIntegerField(default=0)
    
    design_file = models.ForeignKey(
        'design_files.DesignFile',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='variants',
    )
    
    class Meta:
        db_table = 'variants'
        indexes = [
            GinIndex(fields=['attributes']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['barcode']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(base_price__gte=0),
                name='variant_base_price_nonneg',
            ),
            models.CheckConstraint(
                check=models.Q(infill_percent__gte=0) & models.Q(infill_percent__lte=100),
                name='variant_infill_range',
            ),
        ]
    
    def __str__(self):
        return f"{self.sku} ({self.product.name})"
    
    def clean(self):
        # Validation business rules ở model level
        super().clean()
        if self.status == self.Status.ACTIVE and not self.design_file:
            from django.core.exceptions import ValidationError
            raise ValidationError("Active variant requires a design file.")
```

### 4. ViewSet pattern

```python
# apps/skus/views/variant.py
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from apps.skus.models import Variant
from apps.skus.serializers import (
    VariantCreateInputSerializer,
    VariantUpdateInputSerializer,
    VariantDetailSerializer,
    VariantListSerializer,
)
from apps.skus.services import variant_create, variant_update, variant_archive
from apps.skus.selectors import variant_list, variant_get
from apps.skus.filters import VariantFilter
from apps.skus.permissions import VariantPermission


class VariantViewSet(viewsets.GenericViewSet):
    permission_classes = [VariantPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VariantFilter
    
    def get_queryset(self):
        # Selector cho list
        return variant_list(user=self.request.user)
    
    def get_serializer_class(self):
        return {
            'list': VariantListSerializer,
            'retrieve': VariantDetailSerializer,
        }.get(self.action, VariantDetailSerializer)
    
    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    def retrieve(self, request, pk=None):
        variant = variant_get(id=pk, user=request.user)
        return Response(VariantDetailSerializer(variant).data)
    
    def create(self, request):
        serializer = VariantCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = variant_create(user=request.user, **serializer.validated_data)
        return Response(VariantDetailSerializer(variant).data, status=201)
    
    def partial_update(self, request, pk=None):
        serializer = VariantUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        variant = variant_update(
            id=pk, user=request.user, **serializer.validated_data,
        )
        return Response(VariantDetailSerializer(variant).data)
    
    @action(detail=True, methods=['post'])
    def publish_to_channel(self, request, pk=None):
        """POST /api/v1/variants/{id}/publish_to_channel/"""
        from apps.channels.services import channel_publish_variant
        channel = request.data.get('channel')
        result = channel_publish_variant(
            user=request.user, variant_id=pk, channel=channel,
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)
```

### 5. Async task (Celery) pattern

Marketplace sync **luôn** chạy qua Celery, không sync trong request.

```python
# apps/channels/tasks.py
from celery import shared_task
from celery.exceptions import Retry
from apps.channels.connectors import get_connector
from apps.channels.models import ChannelListing


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def push_variant_to_channel(self, *, variant_id: str, channel: str, shop_id: str):
    """Push variant lên marketplace. Idempotent qua channel_listings.external_product_id."""
    connector = get_connector(channel, shop_id=shop_id)
    listing, _ = ChannelListing.objects.select_for_update().get_or_create(
        variant_id=variant_id, channel=channel, shop_id=shop_id,
    )
    
    if listing.external_product_id:
        # Already pushed → update
        result = connector.update_product(listing)
    else:
        result = connector.create_product(listing)
        listing.external_product_id = result['external_id']
    
    listing.last_synced_at = timezone.now()
    listing.last_sync_status = 'success'
    listing.save()
    return result
```

### 6. Permission pattern (RBAC)

```python
# apps/skus/permissions.py
from rest_framework import permissions


class VariantPermission(permissions.BasePermission):
    """Map actions với role permissions."""
    
    ACTION_PERMISSION = {
        'list': 'variant.read',
        'retrieve': 'variant.read',
        'create': 'variant.create',
        'partial_update': 'variant.update',
        'destroy': 'variant.delete',
        'publish_to_channel': 'channel.publish',
    }
    
    def has_permission(self, request, view):
        required = self.ACTION_PERMISSION.get(view.action)
        if required is None:
            return False
        return request.user.has_perm(required)
    
    def has_object_permission(self, request, view, obj):
        # Cost price chỉ Production Manager + Super Admin xem được
        if view.action == 'retrieve' and request.query_params.get('include_cost'):
            return request.user.has_perm('variant.cost_read')
        return True
```

### 7. Exception handling

```python
# apps/core/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status


class BusinessError(APIException):
    """Base cho business rule violations."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Business rule violation'
    default_code = 'business_error'


class LicenseCommercialBlockError(BusinessError):
    default_detail = 'Design file license does not allow commercial use'
    default_code = 'license_blocks_commercial'


class SkuConflictError(BusinessError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'SKU conflict — please retry'
    default_code = 'sku_conflict'


class TikiOptionAttributesExceededError(BusinessError):
    default_detail = 'Tiki supports max 2 option attributes — please merge axes'
    default_code = 'tiki_option_limit'
```

## Workflow khi sinh code module mới

1. **Đọc spec/user story trước**. Nếu chưa rõ → hỏi user, hoặc tham chiếu skill `ba-spec`.
2. **Liệt kê resources cần generate**:
   - Models (+ migration)
   - Serializers (input + output)
   - ViewSet/URLs
   - Service functions (write)
   - Selector functions (read)
   - Filters, Permissions
   - Celery tasks (nếu có async)
   - Factories cho test
3. **Sinh code theo thứ tự**: models → migrations → serializers → services → selectors → views → urls → permissions → tasks → factories.
4. **Mỗi file đều có docstring + type hints**.
5. **Constants đặt trong module-level CONSTANTS hoặc `apps/{app}/constants.py`**, không hardcode magic numbers.
6. **Validate input ở serializer**, validate business rule ở service.
7. **Audit log mọi write operation** trong service.

## Reference files

- `references/sku_generator.md` — Logic generate SKU đầy đủ
- `references/marketplace_connectors.md` — Skeleton Shopee/Lazada/Tiki
- `references/celery_patterns.md` — Retry, dead letter, idempotency
- `references/django_styleguide.md` — Tóm tắt HackSoft styleguide

## Anti-patterns

❌ Logic trong serializer's `create()`/`update()` → ✅ chỉ validate, delegate sang service  
❌ N+1 query trong serializer → ✅ `prefetch_related`, `select_related` trong selector  
❌ `Product.objects.all()` trong view → ✅ qua selector function  
❌ `try/except` bao toàn bộ view → ✅ DRF exception handler + custom exceptions  
❌ Hard-code marketplace credentials → ✅ qua `django-environ` + `MarketplaceCredential` model  
❌ Sync HTTP call trong request (push Shopee) → ✅ Celery task  
❌ `Model.save()` không trong transaction khi có multi-step → ✅ `@transaction.atomic`  
❌ Skip migration "tạm thời" → ✅ luôn `makemigrations` ngay sau khi đổi model
