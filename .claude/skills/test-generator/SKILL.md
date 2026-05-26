---
name: test-generator
description: Sinh unit/integration/e2e tests cho Django backend (pytest + factory_boy) và Next.js frontend (Vitest + Playwright) cho dự án quản lý SKU in 3D. Use this skill whenever the user mentions "test", "unit test", "integration test", "e2e", "viết test", "tạo test", "pytest", "factory", "fixture", "Playwright", "Vitest", "Jest", or asks about TDD/test coverage — even casually like "test cho function này", "viết test case", "mock cái này". Also triggers for parametrized tests, factory_boy patterns, API contract tests, mocking marketplace APIs, testing Celery tasks, and snapshot tests.
---

# Test Generator cho dự án 3D Printing PIM

Skill này sinh test suite cho backend (Django) và frontend (Next.js). Test phải có ý nghĩa nghiệp vụ, không phải test cho có coverage.

## Stack test

### Backend
- **pytest** + **pytest-django** + **pytest-cov** + **pytest-xdist** (parallel)
- **factory_boy** + **faker** (factories)
- **freezegun** (freeze time)
- **responses** hoặc **httpx_mock** (mock HTTP)
- **pytest-celery** với `CELERY_TASK_ALWAYS_EAGER=True`
- **time-machine** alternative cho freezegun

### Frontend
- **Vitest** (unit + component test)
- **@testing-library/react** + **@testing-library/user-event**
- **MSW (Mock Service Worker)** mock API
- **Playwright** cho e2e
- **vitest-canvas-mock** nếu test 3D viewer

## Test pyramid mục tiêu

```
            /\
           /e2e\         5%  - critical user journeys
          /------\
         /  int   \      25% - service + DB, API endpoints  
        /----------\
       /   unit     \    70% - pure functions, components
      /--------------\
```

## Backend test patterns

### Factories (factory_boy)

```python
# apps/skus/tests/factories.py
import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from apps.catalog.models import Product, Category, Brand
from apps.skus.models import Variant
from apps.materials.models import Material
from apps.design_files.models import DesignFile
from apps.accounts.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'user{n}@test.local')
    username = factory.LazyAttribute(lambda o: o.email)
    role = 'catalog_manager'
    is_active = True
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or 'testpass123')
        if create:
            self.save()


class SuperAdminFactory(UserFactory):
    role = 'super_admin'
    is_superuser = True
    is_staff = True


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
    
    name = factory.Faker('word')
    code_3 = factory.Sequence(lambda n: f'C{n:02d}')
    slug = factory.LazyAttribute(lambda o: o.name.lower())


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = Brand
    
    name = factory.Sequence(lambda n: f'Brand {n}')
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(' ', '-'))


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
    
    name = factory.Faker('catch_phrase')
    slug = factory.Sequence(lambda n: f'product-{n}')
    sku_root = factory.Sequence(lambda n: f'PRD{n:04d}')
    primary_category = factory.SubFactory(CategoryFactory)
    brand = factory.SubFactory(BrandFactory)
    status = Product.Status.DRAFT
    created_by = factory.SubFactory(UserFactory)


class MaterialFactory(DjangoModelFactory):
    class Meta:
        model = Material
    
    code = factory.Sequence(lambda n: f'MAT{n:03d}')
    name = factory.Faker('word')
    type = 'filament'
    subtype = 'pla'
    color = 'red'
    price_per_unit = Decimal('400.00')  # 400 VND/gram
    unit = 'g'


class DesignFileFactory(DjangoModelFactory):
    class Meta:
        model = DesignFile
    
    filename = factory.Sequence(lambda n: f'model_{n}.stl')
    storage_key = factory.LazyAttribute(lambda o: f'design-files/{o.filename}')
    format = 'stl'
    size_bytes = 1024 * 1024
    license_type = DesignFile.License.CC0
    source = DesignFile.Source.ORIGINAL


class DesignFileNCFactory(DesignFileFactory):
    """File với license non-commercial."""
    license_type = DesignFile.License.CC_BY_NC


class VariantFactory(DjangoModelFactory):
    class Meta:
        model = Variant
    
    product = factory.SubFactory(ProductFactory)
    sku = factory.Sequence(lambda n: f'FIG-PRD{n:04d}-PLA-RED-M-01')
    base_price = Decimal('150000')
    cost_price = Decimal('40000')
    material = factory.SubFactory(MaterialFactory)
    material_color = 'red'
    size_preset = 'M'
    status = Variant.Status.DRAFT
```

### Conftest (shared fixtures)

```python
# conftest.py (project root)
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin(db):
    from apps.skus.tests.factories import SuperAdminFactory
    return SuperAdminFactory()


@pytest.fixture
def catalog_manager(db):
    from apps.skus.tests.factories import UserFactory
    return UserFactory(role='catalog_manager')


@pytest.fixture
def authenticated_client(api_client, catalog_manager):
    api_client.force_authenticate(user=catalog_manager)
    return api_client


@pytest.fixture(autouse=True)
def use_dummy_cache(settings):
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
```

### Unit test: Service function

```python
# apps/skus/tests/test_variant_service.py
import pytest
from decimal import Decimal
from apps.skus.services.variant import variant_create
from apps.skus.exceptions import LicenseCommercialBlockError, SkuConflictError
from apps.skus.tests.factories import (
    ProductFactory, VariantFactory, DesignFileFactory, DesignFileNCFactory,
    MaterialFactory, UserFactory,
)


@pytest.mark.django_db
class TestVariantCreate:
    """Tests cho variant_create service.
    
    Coverage targets:
    - Happy path
    - License blocking (BR-003)
    - SKU sequence collision
    - Audit log triggered (BR-009)
    """
    
    def test_creates_variant_with_valid_data(self):
        product = ProductFactory()
        material = MaterialFactory(code='PLA')
        user = UserFactory()
        
        variant = variant_create(
            user=user,
            product_id=product.id,
            axes={'material_id': material.id, 'material_color': 'red', 'size_preset': 'M'},
            base_price=Decimal('150000'),
        )
        
        assert variant.sku.startswith(product.primary_category.code_3)
        assert variant.status == 'draft'
        assert variant.created_by == user
    
    def test_blocks_when_license_disallows_commercial(self):
        """BR-003: Không cho tạo variant active khi license CC BY-NC."""
        product = ProductFactory()
        nc_file = DesignFileNCFactory()
        user = UserFactory()
        
        with pytest.raises(LicenseCommercialBlockError) as exc_info:
            variant_create(
                user=user,
                product_id=product.id,
                axes={},
                base_price=Decimal('100000'),
                design_file_id=nc_file.id,
                status='active',
            )
        
        assert 'commercial' in str(exc_info.value).lower()
    
    def test_allows_draft_status_with_nc_license(self):
        """Draft variant với license NC vẫn được phép — chỉ block khi active."""
        product = ProductFactory()
        nc_file = DesignFileNCFactory()
        user = UserFactory()
        
        variant = variant_create(
            user=user,
            product_id=product.id,
            axes={},
            base_price=Decimal('100000'),
            design_file_id=nc_file.id,
            status='draft',
        )
        assert variant.status == 'draft'
    
    def test_sku_length_in_range_12_to_24(self):
        """BR-002: SKU length 12-24 chars."""
        product = ProductFactory(name='Dragon')
        user = UserFactory()
        
        variant = variant_create(
            user=user, product_id=product.id,
            axes={'material_color': 'red'},
            base_price=Decimal('100000'),
        )
        assert 12 <= len(variant.sku) <= 24
    
    def test_audit_log_created(self):
        """BR-009: Mỗi state change phải có audit log."""
        from apps.core.models import AuditLog
        product = ProductFactory()
        user = UserFactory()
        
        variant = variant_create(
            user=user, product_id=product.id, axes={}, base_price=Decimal('100000'),
        )
        
        log = AuditLog.objects.get(entity_id=str(variant.id))
        assert log.action == 'variant.created'
        assert log.actor == user
    
    @pytest.mark.django_db(transaction=True)
    def test_concurrent_creation_no_sku_collision(self):
        """Race condition test: 2 transaction đồng thời không gen cùng SKU."""
        import threading
        product = ProductFactory()
        user = UserFactory()
        results = []
        errors = []
        
        def create():
            try:
                v = variant_create(
                    user=user, product_id=product.id,
                    axes={'material_color': 'red'},
                    base_price=Decimal('100000'),
                )
                results.append(v.sku)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=create) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert len(errors) == 0
        assert len(set(results)) == 5  # All unique
```

### Parametrized test (license matrix)

```python
@pytest.mark.django_db
@pytest.mark.parametrize('license_type,expected_commercial', [
    ('cc0', True),
    ('cc_by', True),
    ('cc_by_sa', True),
    ('cc_by_nd', True),
    ('cc_by_nc', False),
    ('cc_by_nc_sa', False),
    ('cc_by_nc_nd', False),
])
def test_license_derived_commercial_flag(license_type, expected_commercial):
    """Test save() đúng derive license_allows_commercial cho mọi license type."""
    df = DesignFileFactory(license_type=license_type)
    assert df.license_allows_commercial is expected_commercial
```

### Integration test: API endpoint

```python
# apps/skus/tests/test_variant_api.py
import pytest
from decimal import Decimal
from apps.skus.tests.factories import ProductFactory, VariantFactory, DesignFileNCFactory


@pytest.mark.django_db
class TestVariantCreateAPI:
    URL = '/api/v1/variants/'
    
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, data={})
        assert response.status_code == 401
    
    def test_create_returns_201_with_valid_payload(self, authenticated_client):
        product = ProductFactory()
        response = authenticated_client.post(self.URL, data={
            'product_id': str(product.id),
            'axes': {'material_color': 'red'},
            'base_price': '150000',
        }, format='json')
        
        assert response.status_code == 201
        body = response.json()
        assert 'sku' in body
        assert body['base_price'] == '150000.00'
    
    def test_license_block_returns_400_with_error_code(self, authenticated_client):
        product = ProductFactory()
        nc_file = DesignFileNCFactory()
        
        response = authenticated_client.post(self.URL, data={
            'product_id': str(product.id),
            'axes': {},
            'base_price': '100000',
            'design_file_id': str(nc_file.id),
            'status': 'active',
        }, format='json')
        
        assert response.status_code == 400
        body = response.json()
        assert body['error_code'] == 'LICENSE_BLOCKS_COMMERCIAL'
    
    def test_role_without_perm_returns_403(self, api_client):
        """Cashier không được create variant."""
        from apps.skus.tests.factories import UserFactory
        cashier = UserFactory(role='cashier')
        api_client.force_authenticate(user=cashier)
        product = ProductFactory()
        
        response = api_client.post(self.URL, data={
            'product_id': str(product.id),
            'axes': {},
            'base_price': '100000',
        }, format='json')
        
        assert response.status_code == 403
```

### Celery task test

```python
# apps/channels/tests/test_tasks.py
import pytest
from unittest.mock import patch, MagicMock
import responses

from apps.channels.tasks import push_variant_to_channel, process_shopee_order_webhook
from apps.channels.tests.factories import ChannelListingFactory, MarketplaceCredentialFactory
from apps.skus.tests.factories import VariantFactory


@pytest.mark.django_db
class TestPushVariantToChannel:
    @responses.activate
    def test_creates_listing_on_shopee_success(self, settings):
        """Happy path: gọi Shopee API, lưu external_product_id."""
        settings.SHOPEE_PARTNER_ID = '12345'
        settings.SHOPEE_PARTNER_KEY = 'testkey'
        
        variant = VariantFactory()
        cred = MarketplaceCredentialFactory(channel='shopee', shop_id='shop1')
        
        responses.add(
            responses.POST,
            'https://partner.shopeemobile.com/api/v2/product/add_item',
            json={'response': {'item_id': 999888777}, 'error': None},
        )
        
        push_variant_to_channel(variant_id=str(variant.id), channel='shopee', shop_id='shop1')
        
        listing = variant.channel_listings.get(channel='shopee')
        assert listing.external_product_id == '999888777'
        assert listing.last_sync_status == 'success'
    
    @responses.activate
    def test_retries_on_timeout(self, settings):
        variant = VariantFactory()
        MarketplaceCredentialFactory(channel='shopee', shop_id='shop1')
        
        responses.add(
            responses.POST,
            'https://partner.shopeemobile.com/api/v2/product/add_item',
            body=ConnectionError('Network down'),
        )
        
        from celery.exceptions import Retry
        with pytest.raises(Retry):
            push_variant_to_channel.apply(
                kwargs={'variant_id': str(variant.id), 'channel': 'shopee', 'shop_id': 'shop1'}
            )


@pytest.mark.django_db
class TestProcessShopeeOrderWebhook:
    def test_idempotent_skip_duplicate_event(self):
        """Webhook với event_id đã process → skip."""
        from apps.channels.models import ProcessedEvent
        
        payload = {'event_id': 'evt-123', 'code': 3, 'data': {}}
        ProcessedEvent.objects.create(source='shopee', external_event_id='evt-123', payload=payload)
        
        result = process_shopee_order_webhook(payload)
        assert result['status'] == 'skipped'
```

### Marketplace connector test

```python
# apps/channels/tests/test_tiki_connector.py
import pytest
from apps.channels.connectors.tiki import TikiConnector
from apps.channels.exceptions import TikiOptionAttributesExceededError
from apps.skus.tests.factories import ProductFactory, VariantFactory


@pytest.mark.django_db
class TestTikiConnectorAxesLimit:
    """BR-004: Tiki max 2 option attributes."""
    
    def test_blocks_when_3_axes(self):
        product = ProductFactory()
        # Tạo variant với 3 axes
        VariantFactory(
            product=product,
            material_color='red', size_preset='M',
            layer_resolution_mm='0.2', status='active',
        )
        
        connector = TikiConnector(credentials=...)
        with pytest.raises(TikiOptionAttributesExceededError) as exc:
            connector.create_product(listing=...)
        
        assert 'Tiki supports max 2' in str(exc.value)
    
    def test_allows_2_axes(self):
        product = ProductFactory()
        VariantFactory(
            product=product,
            material_color='red', size_preset='M',
            status='active',
        )
        # Should not raise
        connector = TikiConnector(credentials=...)
        # ... mock API and verify call
```

### SQL/DB test

```python
@pytest.mark.django_db
class TestVariantQueries:
    """Test schema indexes + common queries."""
    
    def test_filter_by_attributes_uses_gin_index(self, django_assert_num_queries):
        product = ProductFactory()
        VariantFactory(product=product, attributes={'finish': 'matte', 'food_safe': True})
        VariantFactory(product=product, attributes={'finish': 'glossy'})
        
        with django_assert_num_queries(1):
            results = list(Variant.objects.filter(attributes__contains={'finish': 'matte'}))
        assert len(results) == 1
    
    def test_only_one_current_poc_per_variant(self):
        """Unique constraint: 1 variant chỉ có 1 POC current."""
        from apps.poc.tests.factories import POCVersionFactory
        from django.db import IntegrityError
        
        variant = VariantFactory()
        POCVersionFactory(variant=variant, is_current=True)
        
        with pytest.raises(IntegrityError):
            POCVersionFactory(variant=variant, is_current=True)
```

## Frontend test patterns

### Component test (Vitest + RTL)

```ts
// components/variant/__tests__/variant-create-form.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VariantCreateForm } from '../variant-create-form';
import * as variantsApi from '@/lib/api/variants';

vi.mock('@/lib/api/variants');

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('VariantCreateForm', () => {
  it('submits valid data', async () => {
    const createMock = vi.spyOn(variantsApi.variantsApi, 'create').mockResolvedValue({
      id: 'v1', sku: 'FIG-001-PLA-RED-M-01', base_price: 150000,
    } as any);
    
    const onSuccess = vi.fn();
    renderWithProviders(<VariantCreateForm productId="p1" onSuccess={onSuccess} />);
    
    await userEvent.type(screen.getByLabelText(/màu vật liệu/i), 'red');
    await userEvent.clear(screen.getByLabelText(/giá bán/i));
    await userEvent.type(screen.getByLabelText(/giá bán/i), '150000');
    await userEvent.click(screen.getByRole('button', { name: /tạo variant/i }));
    
    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith({
        product_id: 'p1',
        axes: { material_color: 'red' },
        base_price: 150000,
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });
  
  it('shows validation error for negative price', async () => {
    renderWithProviders(<VariantCreateForm productId="p1" />);
    
    await userEvent.type(screen.getByLabelText(/giá bán/i), '-100');
    await userEvent.click(screen.getByRole('button', { name: /tạo variant/i }));
    
    expect(await screen.findByText(/phải lớn hơn hoặc bằng 0/i)).toBeInTheDocument();
  });
  
  it('disables submit while pending', async () => {
    vi.spyOn(variantsApi.variantsApi, 'create').mockImplementation(
      () => new Promise(() => {}) // never resolves
    );
    
    renderWithProviders(<VariantCreateForm productId="p1" />);
    await userEvent.type(screen.getByLabelText(/giá bán/i), '100');
    await userEvent.click(screen.getByRole('button', { name: /tạo variant/i }));
    
    expect(screen.getByRole('button', { name: /đang tạo/i })).toBeDisabled();
  });
});
```

### MSW handlers

```ts
// src/test/msw/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/v1/variants/', () => {
    return HttpResponse.json({
      count: 2,
      results: [
        { id: 'v1', sku: 'FIG-001-PLA-RED-M-01', base_price: '150000.00', status: 'active' },
        { id: 'v2', sku: 'FIG-001-PLA-BLU-M-01', base_price: '150000.00', status: 'draft' },
      ],
    });
  }),
  
  http.post('/api/v1/variants/', async ({ request }) => {
    const body = await request.json() as any;
    if (body.design_file_id === 'nc-file') {
      return HttpResponse.json(
        { error_code: 'LICENSE_BLOCKS_COMMERCIAL', message: 'License does not allow commercial use' },
        { status: 400 }
      );
    }
    return HttpResponse.json({ id: 'new-v', sku: 'NEW-01', ...body }, { status: 201 });
  }),
];
```

### Playwright e2e

```ts
// e2e/variant-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Variant creation flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name=email]', 'catalog@test.local');
    await page.fill('[name=password]', 'testpass');
    await page.click('button[type=submit]');
    await page.waitForURL('/products');
  });
  
  test('catalog manager can create variant', async ({ page }) => {
    await page.goto('/products/p1/variants/new');
    await page.fill('[name="axes.material_color"]', 'red');
    await page.fill('[name="base_price"]', '150000');
    await page.click('button:has-text("Tạo variant")');
    
    await expect(page.locator('.sonner-toast')).toContainText('thành công');
    await expect(page).toHaveURL(/\/variants\//);
  });
  
  test('blocks active variant when design file is NC license', async ({ page }) => {
    await page.goto('/products/p1/variants/new');
    await page.selectOption('[name=design_file_id]', { label: 'nc-licensed-file.stl' });
    await page.selectOption('[name=status]', 'active');
    await page.fill('[name="base_price"]', '100000');
    await page.click('button:has-text("Tạo variant")');
    
    await expect(page.locator('.sonner-toast')).toContainText('không cho phép bán thương mại');
  });
});
```

## Coverage targets

| Layer | Coverage target |
|---|---|
| Services (business logic) | 90%+ |
| Selectors | 80%+ |
| Models (custom methods) | 80%+ |
| ViewSets / Serializers | 70%+ |
| Celery tasks | 80%+ |
| Marketplace connectors | 70%+ với mock |
| Frontend components | 70%+ |
| Frontend hooks | 80%+ |
| E2E critical paths | 100% (login, create variant, push to channel, POS checkout) |

## Test naming convention

- `test_<what>_<expected>_when_<condition>`
- Examples:
  - `test_creates_variant_when_valid_data`
  - `test_blocks_publish_when_license_is_nc`
  - `test_returns_403_when_role_lacks_permission`

## What to test (prioritization)

🔴 **Must test**:
- Business rules BR-001 → BR-010 (mỗi rule ít nhất 1 test)
- Auth & permission (mỗi role × mỗi resource)
- Money calculation (POC cost, channel price)
- SKU generation (uniqueness, length, format)
- License compliance (block commercial)
- Marketplace API contract (mocked)
- Webhook idempotency
- Race conditions (concurrent SKU gen, stock decrement)

🟡 **Should test**:
- Edge cases trong checklist BA spec
- Migration rollback
- Filter/search/pagination
- File upload validation

🟢 **Nice to have**:
- Snapshot tests cho UI components ổn định
- Performance regression (response time < threshold)
- Accessibility (axe-core)

## Anti-patterns

❌ Test chỉ assert "không lỗi" — phải assert behavior cụ thể  
❌ 1 test có > 5 assertions không liên quan → tách nhỏ  
❌ Mock quá sâu (mock cả internal function) → mock ở boundary  
❌ Hardcode datetime/UUID → dùng freezegun + factory  
❌ Test phụ thuộc thứ tự chạy → mỗi test phải độc lập  
❌ `sleep()` để chờ async → `waitFor` / `freezegun`  
❌ Mock toàn DB → dùng `@pytest.mark.django_db` thật  
❌ Test private function → test qua public API  
❌ "Happy path" only → luôn có error case + edge case
