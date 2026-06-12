"""Skus-specific pytest fixtures."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.catalog.tests.factories import ProductFactory, UserFactory

from .factories import VariantFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def product(db):
    """Product status=active — sẵn sàng nhận variant."""
    return ProductFactory(status=Product.Status.ACTIVE)


@pytest.fixture
def variant(db, product):
    return VariantFactory(product=product)


@pytest.fixture
def auth_client(db):
    """APIClient với user is_superuser=True (bypass mọi permission gate).

    Sau feature 03, viewset dùng ActionPermission. is_superuser=True
    short-circuit ở permission class (chuẩn Django) → tests cũ
    không cần seed role/permission.
    """
    user = UserFactory(is_superuser=True, is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client
