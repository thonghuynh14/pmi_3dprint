"""Integration tests cho VariantViewSet + ProductVariantMatrixView.

Cover SPEC AC + auth + status codes.
"""

from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.catalog.tests.factories import ProductFactory

URL_LIST = "/api/v1/skus/variants/"


def _detail(pk):
    return f"/api/v1/skus/variants/{pk}/"


def _restore_url(pk):
    return f"/api/v1/skus/variants/{pk}/restore/"


def _matrix_url(product_id):
    return f"/api/v1/catalog/products/{product_id}/variants/bulk-matrix/"


def _create_payload(product_id, **overrides) -> dict:
    base = {
        "product_id": str(product_id),
        "material_name": "PLA",
        "material_code3": "PLA",
        "color_name": "Red",
        "color_code3": "RED",
        "size_preset": "M",
        "base_price": "150000",
    }
    base.update(overrides)
    return base


# =============================================================================
# Authentication (SPEC AC12)
# =============================================================================
@pytest.mark.django_db
class TestAuth:
    def test_list_unauth_returns_401(self):
        response = APIClient().get(URL_LIST)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_unauth_returns_401(self, product):
        response = APIClient().post(
            URL_LIST, _create_payload(product.id), format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Create
# =============================================================================
@pytest.mark.django_db
class TestCreate:
    def test_returns_201_with_full_output(self, auth_client, product):
        response = auth_client.post(
            URL_LIST, _create_payload(product.id), format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["sku"] == f"{product.sku_root}-PLA-RED-M-01"
        assert body["sequence_no"] == 1
        assert body["product_id"] == str(product.id)
        assert body["base_price"] == "150000.00"

    def test_invalid_code3_returns_400(self, auth_client, product):
        response = auth_client.post(
            URL_LIST,
            _create_payload(product.id, material_code3="PLAID"),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_size_preset_returns_400(self, auth_client, product):
        response = auth_client.post(
            URL_LIST,
            _create_payload(product.id, size_preset="has space"),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_negative_price_returns_400(self, auth_client, product):
        response = auth_client.post(
            URL_LIST,
            _create_payload(product.id, base_price="-100"),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_combo_returns_409(self, auth_client, product):
        auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        response = auth_client.post(
            URL_LIST, _create_payload(product.id), format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_product_archived_returns_400(self, auth_client):
        archived = ProductFactory(status=Product.Status.ARCHIVED)
        response = auth_client.post(
            URL_LIST, _create_payload(archived.id), format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# List
# =============================================================================
@pytest.mark.django_db
class TestList:
    def _create_3(self, auth_client, product):
        for color, code in [("Red", "RED"), ("Blue", "BLU"), ("Green", "GRN")]:
            auth_client.post(
                URL_LIST,
                _create_payload(product.id, color_name=color, color_code3=code),
                format="json",
            )

    def test_paginated(self, auth_client, product):
        self._create_3(auth_client, product)
        response = auth_client.get(URL_LIST)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 3

    def test_filter_by_product(self, auth_client, product):
        auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        other = ProductFactory(status=Product.Status.ACTIVE)
        auth_client.post(URL_LIST, _create_payload(other.id), format="json")
        response = auth_client.get(URL_LIST, {"product": str(product.id)})
        assert response.json()["count"] == 1

    def test_search_filters_by_sku_or_name(self, auth_client, product):
        self._create_3(auth_client, product)
        response = auth_client.get(URL_LIST, {"search": "RED"})
        assert response.json()["count"] == 1

    def test_status_filter(self, auth_client, product):
        auth_client.post(
            URL_LIST,
            _create_payload(product.id, status="draft"),
            format="json",
        )
        auth_client.post(
            URL_LIST,
            _create_payload(
                product.id, color_name="Blue", color_code3="BLU", status="active",
            ),
            format="json",
        )
        response = auth_client.get(URL_LIST, {"status": "active"})
        assert response.json()["count"] == 1

    def test_default_excludes_archived(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        auth_client.delete(_detail(r1.json()["id"]))
        response = auth_client.get(URL_LIST)
        assert response.json()["count"] == 0

    def test_show_archived_includes(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        auth_client.delete(_detail(r1.json()["id"]))
        response = auth_client.get(URL_LIST, {"show_archived": "true"})
        assert response.json()["count"] == 1


# =============================================================================
# Retrieve
# =============================================================================
@pytest.mark.django_db
class TestRetrieve:
    def test_returns_200(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        response = auth_client.get(_detail(r1.json()["id"]))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_404_for_unknown(self, auth_client):
        response = auth_client.get(_detail("00000000-0000-0000-0000-000000000000"))
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Patch (update)
# =============================================================================
@pytest.mark.django_db
class TestPatch:
    def test_updates_base_price(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        response = auth_client.patch(
            _detail(r1.json()["id"]),
            {"base_price": "200000"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["base_price"] == "200000.00"

    def test_immutable_field_returns_400(self, auth_client, product):
        """SPEC AC9."""
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        response = auth_client.patch(
            _detail(r1.json()["id"]),
            {"material_code3": "ABS"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Destroy + Restore
# =============================================================================
@pytest.mark.django_db
class TestDestroyRestore:
    def test_destroy_returns_204(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        response = auth_client.delete(_detail(r1.json()["id"]))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_restore_returns_200(self, auth_client, product):
        r1 = auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        v_id = r1.json()["id"]
        auth_client.delete(_detail(v_id))
        response = auth_client.post(_restore_url(v_id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted_at"] is None


# =============================================================================
# Matrix endpoint
# =============================================================================
@pytest.mark.django_db
class TestMatrixEndpoint:
    def test_creates_NxMxP_returns_201(self, auth_client, product):
        payload = {
            "materials": [
                {"name": "PLA", "code3": "PLA"},
                {"name": "PETG", "code3": "PET"},
            ],
            "colors": [
                {"name": "Red", "code3": "RED"},
                {"name": "Blue", "code3": "BLU"},
            ],
            "sizes": ["S", "M"],
            "base_price": "150000",
        }
        response = auth_client.post(
            _matrix_url(product.id), payload, format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["count"] == 8
        assert len(body["created"]) == 8

    def test_too_large_returns_400(self, auth_client, product):
        payload = {
            "materials": [
                {"name": f"M{i}", "code3": f"M{i:02d}"} for i in range(11)
            ],
            "colors": [
                {"name": f"C{i}", "code3": f"C{i:02d}"} for i in range(11)
            ],
            "sizes": ["M"],
            "base_price": "100",
        }
        response = auth_client.post(
            _matrix_url(product.id), payload, format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_in_input_returns_400(self, auth_client, product):
        payload = {
            "materials": [
                {"name": "PLA", "code3": "PLA"},
                {"name": "PLA dup", "code3": "pla"},
            ],
            "colors": [{"name": "Red", "code3": "RED"}],
            "sizes": ["M"],
            "base_price": "100",
        }
        response = auth_client.post(
            _matrix_url(product.id), payload, format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_combo_overlap_returns_409(self, auth_client, product):
        auth_client.post(URL_LIST, _create_payload(product.id), format="json")
        payload = {
            "materials": [{"name": "PLA", "code3": "PLA"}],
            "colors": [
                {"name": "Red", "code3": "RED"},
                {"name": "Blue", "code3": "BLU"},
            ],
            "sizes": ["M"],
            "base_price": "100",
        }
        response = auth_client.post(
            _matrix_url(product.id), payload, format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_unauth_returns_401(self, product):
        payload = {
            "materials": [{"name": "PLA", "code3": "PLA"}],
            "colors": [{"name": "Red", "code3": "RED"}],
            "sizes": ["M"],
            "base_price": "100",
        }
        response = APIClient().post(
            _matrix_url(product.id), payload, format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
