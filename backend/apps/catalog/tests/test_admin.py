"""Smoke tests cho Django Admin Product registration.

Mục đích chính: chứng minh ProductAdmin load được, có thể list / detail
qua admin UI. Không cover full admin form workflow (Django đảm bảo).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from .factories import ProductFactory


@pytest.fixture
def admin_client(db):
    """Django test client logged-in dưới quyền superuser."""
    User = get_user_model()
    User.objects.filter(username="adminer").delete()
    admin = User.objects.create_superuser("adminer", "a@test.local", "pw")
    client = Client()
    client.force_login(admin)
    return client


@pytest.mark.django_db
class TestProductAdmin:
    def test_changelist_accessible(self, admin_client):
        response = admin_client.get(reverse("admin:catalog_product_changelist"))
        assert response.status_code == 200
        # Tiêu đề admin app
        content = response.content.decode()
        assert "Product" in content or "products" in content.lower()

    def test_changelist_shows_alive_and_deleted_products(self, admin_client):
        alive = ProductFactory(name="Alive Product")
        archived = ProductFactory(name="Archived Product")
        archived.delete()

        response = admin_client.get(reverse("admin:catalog_product_changelist"))
        content = response.content.decode()
        # get_queryset override -> Product.all_objects -> cả 2 hiện trong list
        assert "Alive Product" in content
        assert "Archived Product" in content

    def test_changelist_search(self, admin_client):
        target = ProductFactory(name="Unique Dragon Name")
        ProductFactory(name="Other")
        response = admin_client.get(
            reverse("admin:catalog_product_changelist"),
            {"q": "Dragon"},
        )
        content = response.content.decode()
        assert "Unique Dragon Name" in content

    def test_change_view_accessible(self, admin_client):
        product = ProductFactory()
        response = admin_client.get(
            reverse("admin:catalog_product_change", args=(product.pk,)),
        )
        assert response.status_code == 200

    def test_add_view_accessible(self, admin_client):
        response = admin_client.get(reverse("admin:catalog_product_add"))
        assert response.status_code == 200

    def test_save_model_assigns_created_by(self, admin_client):
        from apps.catalog.models import Product

        response = admin_client.post(
            reverse("admin:catalog_product_add"),
            {
                "name": "Admin Created",
                "slug": "admin-created",
                "sku_root": "ADMC01",
                "status": "draft",
                "short_description": "",
                "long_description": "",
                "brand": "",
                "tags": "[]",
                "attributes": "{}",
            },
        )
        # Admin redirect sau khi save → 302
        assert response.status_code == 302
        product = Product.objects.get(slug="admin-created")
        assert product.created_by is not None
        assert product.created_by.username == "adminer"

    def test_action_soft_delete_selected(self, admin_client):
        from apps.catalog.models import Product

        p1 = ProductFactory()
        p2 = ProductFactory()
        # Trigger admin action qua POST changelist
        admin_client.post(
            reverse("admin:catalog_product_changelist"),
            {
                "action": "soft_delete_selected",
                "_selected_action": [str(p1.pk), str(p2.pk)],
                "index": "0",
            },
        )
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.deleted_at is not None
        assert p2.deleted_at is not None
        assert Product.objects.count() == 0
        assert Product.all_objects.count() == 2

    def test_action_restore_selected(self, admin_client):
        from apps.catalog.models import Product

        p = ProductFactory()
        p.delete()
        assert p.deleted_at is not None

        admin_client.post(
            reverse("admin:catalog_product_changelist"),
            {
                "action": "restore_selected",
                "_selected_action": [str(p.pk)],
                "index": "0",
            },
        )
        p.refresh_from_db()
        assert p.deleted_at is None
        assert Product.objects.filter(pk=p.pk).exists()
