"""Catalog-specific pytest fixtures.

Fixtures generic (api_client, ...) đặt ở backend/conftest.py.
"""

import pytest

from .factories import ProductFactory, UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def product(db):
    return ProductFactory()
