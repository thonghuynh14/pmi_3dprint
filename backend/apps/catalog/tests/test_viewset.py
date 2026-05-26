"""Integration tests cho ProductViewSet.

Cover SPEC AC-1 → AC-10 + race condition concurrent create.
"""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.core.models import AuditLog

from .factories import ProductFactory, UserFactory

URL_LIST = "/api/v1/catalog/products/"


def _detail(pk):
    return f"/api/v1/catalog/products/{pk}/"


def _restore(pk):
    return f"/api/v1/catalog/products/{pk}/restore/"


@pytest.fixture
def auth_client(db):
    """APIClient đã authenticated với user mới tạo."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user  # đính kèm để test assert created_by
    return client


# ---------------------------------------------------------------------------
# LIST endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListEndpoint:
    def test_unauthenticated_returns_401(self):
        response = APIClient().get(URL_LIST)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_paginated_results(self, auth_client):
        ProductFactory.create_batch(3)
        response = auth_client.get(URL_LIST)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["count"] == 3
        assert len(body["results"]) == 3
        assert "next" in body and "previous" in body

    def test_search_filters_results(self, auth_client):
        dragon = ProductFactory(name="Dragon Figure")
        ProductFactory(name="Phone Case")
        ProductFactory(name="Vase")

        response = auth_client.get(URL_LIST, {"search": "dragon"})
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.json()["results"]]
        assert ids == [str(dragon.pk)]

    def test_status_filter_works(self, auth_client):
        active = ProductFactory(status=Product.Status.ACTIVE)
        ProductFactory(status=Product.Status.DRAFT)

        response = auth_client.get(URL_LIST, {"status": "active"})
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.json()["results"]]
        assert ids == [str(active.pk)]

    def test_default_excludes_archived(self, auth_client):
        alive = ProductFactory()
        archived = ProductFactory()
        archived.delete()

        response = auth_client.get(URL_LIST)
        ids = {item["id"] for item in response.json()["results"]}
        assert ids == {str(alive.pk)}

    def test_show_archived_includes_deleted(self, auth_client):
        alive = ProductFactory()
        archived = ProductFactory()
        archived.delete()

        response = auth_client.get(URL_LIST, {"show_archived": "true"})
        ids = {item["id"] for item in response.json()["results"]}
        assert ids == {str(alive.pk), str(archived.pk)}

    def test_list_response_uses_list_item_serializer(self, auth_client):
        ProductFactory(long_description="hidden in list", attributes={"k": "v"})
        response = auth_client.get(URL_LIST)
        item = response.json()["results"][0]
        # Hẹp: không có long_description, attributes, created_by
        assert "long_description" not in item
        assert "attributes" not in item
        assert "created_by" not in item


# ---------------------------------------------------------------------------
# RETRIEVE endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRetrieveEndpoint:
    def test_returns_full_object(self, auth_client):
        product = ProductFactory(
            long_description="full detail here",
            attributes={"scale": "1:10"},
        )
        response = auth_client.get(_detail(product.pk))
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        # Full = include long_description, attributes, nested user
        assert body["long_description"] == "full detail here"
        assert body["attributes"] == {"scale": "1:10"}
        assert "created_by" in body  # nested

    def test_missing_id_returns_404(self, auth_client):
        response = auth_client.get(_detail("00000000-0000-0000-0000-000000000000"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_uuid_returns_404(self, auth_client):
        response = auth_client.get(_detail("not-a-uuid"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_default_returns_404(self, auth_client):
        product = ProductFactory()
        product.delete()
        response = auth_client.get(_detail(product.pk))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_with_show_archived_returns_object(self, auth_client):
        product = ProductFactory()
        product.delete()
        response = auth_client.get(
            _detail(product.pk), {"show_archived": "true"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted_at"] is not None


# ---------------------------------------------------------------------------
# CREATE endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateEndpoint:
    def test_valid_returns_201_with_object(self, auth_client):
        response = auth_client.post(
            URL_LIST,
            {"name": "Dragon", "sku_root": "DRAGON"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == "Dragon"
        assert body["sku_root"] == "DRAGON"
        assert body["slug"] == "dragon"  # auto-generated
        assert body["status"] == "draft"
        assert body["created_by"]["id"] == auth_client.user.id

    def test_missing_required_returns_400(self, auth_client):
        response = auth_client.post(URL_LIST, {"name": "no sku"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "sku_root" in response.json()

    def test_invalid_sku_root_format_returns_400(self, auth_client):
        response = auth_client.post(
            URL_LIST,
            {"name": "X", "sku_root": "ab"},  # too short
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = response.json()
        assert "sku_root" in body
        assert "3-8 ký tự" in body["sku_root"][0]

    def test_invalid_slug_format_returns_400(self, auth_client):
        response = auth_client.post(
            URL_LIST,
            {"name": "X", "sku_root": "ABC", "slug": "Has Spaces"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "slug" in response.json()

    def test_invalid_attribute_key_returns_400(self, auth_client):
        response = auth_client.post(
            URL_LIST,
            {
                "name": "X",
                "sku_root": "ABC",
                "attributes": {"bad key with spaces": "value"},
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_slug_returns_409(self, auth_client):
        ProductFactory(slug="taken")
        response = auth_client.post(
            URL_LIST,
            {"name": "X", "sku_root": "AAA", "slug": "taken"},
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "slug" in response.json()["detail"].lower()

    def test_duplicate_sku_root_case_insensitive_returns_409(self, auth_client):
        ProductFactory(sku_root="DRAGON")
        response = auth_client.post(
            URL_LIST,
            {"name": "X", "sku_root": "dragon"},  # lowercase
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "sku_root" in response.json()["detail"].lower()

    def test_writes_audit_log(self, auth_client):
        response = auth_client.post(
            URL_LIST,
            {"name": "X", "sku_root": "X01"},
            format="json",
        )
        pid = response.json()["id"]
        log = AuditLog.objects.get(
            entity_type=ContentType.objects.get_for_model(Product),
            entity_id=pid,
        )
        assert log.action == AuditLog.Action.CREATE
        assert log.actor == auth_client.user

    def test_unauthenticated_create_returns_401(self):
        response = APIClient().post(
            URL_LIST, {"name": "X", "sku_root": "X01"}, format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# PARTIAL UPDATE endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartialUpdateEndpoint:
    def test_only_provided_fields_change(self, auth_client):
        product = ProductFactory(name="Old", short_description="orig desc")
        response = auth_client.patch(
            _detail(product.pk),
            {"name": "New"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["name"] == "New"
        assert body["short_description"] == "orig desc"

    def test_returns_updated_object(self, auth_client):
        from datetime import datetime

        product = ProductFactory(name="Old")
        before_updated_at = product.updated_at

        response = auth_client.patch(
            _detail(product.pk),
            {"name": "Updated"},
            format="json",
        )
        body = response.json()
        assert body["id"] == str(product.pk)
        assert body["name"] == "Updated"

        # updated_at được bump sau update (so sánh giá trị, không phải
        # string vì DRF render TIME_ZONE +07:00 còn DB lưu UTC).
        product.refresh_from_db()
        assert product.updated_at > before_updated_at
        assert datetime.fromisoformat(body["updated_at"]) == product.updated_at

    def test_invalid_field_value_returns_400(self, auth_client):
        product = ProductFactory()
        response = auth_client.patch(
            _detail(product.pk),
            {"sku_root": "ab"},  # invalid format
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_404_for_missing_product(self, auth_client):
        response = auth_client.patch(
            _detail("00000000-0000-0000-0000-000000000000"),
            {"name": "X"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_method_not_allowed_returns_405(self, auth_client):
        product = ProductFactory()
        response = auth_client.put(
            _detail(product.pk),
            {"name": "X", "sku_root": "X01"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------------------
# DELETE + RESTORE endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteRestoreEndpoint:
    def test_delete_soft_deletes_returns_204(self, auth_client):
        product = ProductFactory()
        response = auth_client.delete(_detail(product.pk))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        product.refresh_from_db()
        assert product.deleted_at is not None
        assert product.deleted_by == auth_client.user

    def test_delete_writes_audit_log(self, auth_client):
        product = ProductFactory()
        auth_client.delete(_detail(product.pk))
        log = AuditLog.objects.filter(
            entity_type=ContentType.objects.get_for_model(Product),
            entity_id=str(product.pk),
            action=AuditLog.Action.DELETE,
        )
        assert log.count() == 1
        assert log.first().actor == auth_client.user

    def test_delete_missing_returns_404(self, auth_client):
        response = auth_client.delete(
            _detail("00000000-0000-0000-0000-000000000000"),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restore_clears_deleted_at_returns_200(self, auth_client):
        product = ProductFactory()
        product.delete()

        response = auth_client.post(_restore(product.pk))
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["deleted_at"] is None

    def test_restore_writes_audit_log(self, auth_client):
        product = ProductFactory()
        product.delete()
        auth_client.post(_restore(product.pk))

        log = AuditLog.objects.filter(
            entity_type=ContentType.objects.get_for_model(Product),
            entity_id=str(product.pk),
            action=AuditLog.Action.RESTORE,
        )
        assert log.count() == 1

    def test_restore_conflict_returns_409(self, auth_client):
        """SPEC EC-12: slug đã tái sử dụng → 409 khi restore."""
        first = ProductFactory(slug="shared")
        first.delete()
        ProductFactory(slug="shared")  # reuse

        response = auth_client.post(_restore(first.pk))
        assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# Race condition (concurrent create same sku_root)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestConcurrentCreate:
    """SPEC AC-3 + partial unique index dưới load.

    2 thread cùng POST tạo Product với cùng sku_root → đúng 1 thành công,
    1 thất bại với 409. Partial unique trên LOWER(sku_root) WHERE
    deleted_at IS NULL là cơ chế chắc chắn.
    """

    def test_concurrent_create_same_sku_root_one_succeeds_one_fails(self):
        import threading

        from django.db import connections

        user = UserFactory()
        results: list[int] = []

        def attempt(label: str) -> None:
            client = APIClient()
            client.force_authenticate(user=user)
            try:
                response = client.post(
                    URL_LIST,
                    {"name": f"Product {label}", "sku_root": "RACE01"},
                    format="json",
                )
                results.append(response.status_code)
            finally:
                # Mỗi thread phải close connection riêng (Django thread-local)
                connections.close_all()

        # Start 5 thread cùng lúc
        threads = [threading.Thread(target=attempt, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Kết quả: 1 thread 201, 4 thread 409.
        assert results.count(status.HTTP_201_CREATED) == 1, results
        assert results.count(status.HTTP_409_CONFLICT) == 4, results

        # Verify chỉ 1 product alive với sku_root='RACE01'
        assert Product.objects.filter(sku_root="RACE01").count() == 1
