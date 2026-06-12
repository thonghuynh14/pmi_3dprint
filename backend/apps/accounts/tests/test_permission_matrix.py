"""Permission matrix tests: 6 role × N action × 3 viewset = ~90 assertions.

Approach: parametrize matrix [(role, endpoint, http_method, expected_status)],
authenticate via cookie login flow để chứng minh cả CookieJWTAuth +
ActionPermission cooperate đúng.

Endpoint test:
- GET /catalog/products/         → product:read
- POST /catalog/products/        → product:create
- GET /skus/variants/            → variant:read
- POST /skus/variants/           → variant:create
- POST /catalog/products/<id>/variants/bulk-matrix/ → variant:create
"""

from __future__ import annotations

import pytest

from apps.accounts.tests.factories import make_user


LOGIN_URL = "/api/v1/auth/login/"


@pytest.fixture
def login(api_client, db):
    """Closure login user theo role_code, trả về user + api_client đã set cookie."""

    def _login(role_code: str, password: str = "pw"):
        user = make_user(role_code, username=f"{role_code}_matrix", password=password)
        response = api_client.post(
            LOGIN_URL,
            data={"username": user.username, "password": password},
            format="json",
        )
        assert response.status_code == 200, response.data
        return user

    return _login


# ---------------------------------------------------------------------------
# Matrix: read endpoints (mọi authenticated role → 200)
# ---------------------------------------------------------------------------

READ_ENDPOINTS = [
    "/api/v1/catalog/products/",
    "/api/v1/skus/variants/",
]

ROLES = [
    "super_admin",
    "catalog_manager",
    "production_manager",
    "channel_operator",
    "designer",
    "cashier",
]


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ROLES)
@pytest.mark.parametrize("endpoint", READ_ENDPOINTS)
def test_all_roles_can_read(api_client, login, role_code, endpoint):
    """Mọi role có product:read + variant:read (ai cũng đọc được catalog)."""
    login(role_code)
    response = api_client.get(endpoint)
    assert response.status_code == 200, (
        f"{role_code} bị block trên {endpoint}: {response.status_code} {response.data}"
    )


# ---------------------------------------------------------------------------
# Matrix: product:create — chỉ super_admin + catalog_manager được
# ---------------------------------------------------------------------------

CAN_CREATE_PRODUCT = {"super_admin", "catalog_manager"}


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ROLES)
def test_product_create_permission_matrix(api_client, login, role_code):
    login(role_code)
    response = api_client.post(
        "/api/v1/catalog/products/",
        data={"name": f"Test {role_code}", "sku_root": f"ROL{role_code[:3].upper()}"},
        format="json",
    )
    if role_code in CAN_CREATE_PRODUCT:
        assert response.status_code == 201, (
            f"{role_code} should be allowed: {response.data}"
        )
    else:
        assert response.status_code == 403, (
            f"{role_code} should be denied: got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# Matrix: variant:create — chỉ super_admin + catalog_manager được
# ---------------------------------------------------------------------------

CAN_CREATE_VARIANT = {"super_admin", "catalog_manager"}


@pytest.fixture
def product_for_variant(db):
    """Tạo product sẵn để variant test gắn vào."""
    from apps.catalog.tests.factories import ProductFactory

    return ProductFactory()


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ROLES)
def test_variant_create_permission_matrix(
    api_client, login, role_code, product_for_variant
):
    login(role_code)
    response = api_client.post(
        "/api/v1/skus/variants/",
        data={
            "product_id": str(product_for_variant.id),
            "material_name": "PLA",
            "material_code3": "PLA",
            "color_name": "Red",
            "color_code3": "RED",
            "size_preset": "M",
            "base_price": "150000",
        },
        format="json",
    )
    if role_code in CAN_CREATE_VARIANT:
        assert response.status_code == 201, (
            f"{role_code} should be allowed: {response.data}"
        )
    else:
        assert response.status_code == 403, (
            f"{role_code} should be denied: got {response.status_code}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", ROLES)
def test_matrix_bulk_permission_matrix(
    api_client, login, role_code, product_for_variant
):
    """POST /products/<id>/variants/bulk-matrix/ cần variant:create."""
    login(role_code)
    response = api_client.post(
        f"/api/v1/catalog/products/{product_for_variant.id}/variants/bulk-matrix/",
        data={
            "materials": [{"name": "PLA", "code3": "PLA"}],
            "colors": [{"name": "Red", "code3": "RED"}],
            "sizes": ["M"],
            "base_price": "150000",
        },
        format="json",
    )
    if role_code in CAN_CREATE_VARIANT:
        assert response.status_code == 201, (
            f"{role_code} should be allowed: {response.data}"
        )
    else:
        assert response.status_code == 403, (
            f"{role_code} should be denied: got {response.status_code}"
        )
