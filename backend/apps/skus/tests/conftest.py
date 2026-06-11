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
    """APIClient đã authenticate với user mới."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user  # đính kèm để test assert created_by
    return client
