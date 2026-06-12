"""pytest fixtures cho accounts tests."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory, make_user


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def super_admin(db):
    return make_user("super_admin", username="super_admin_user")


@pytest.fixture
def catalog_manager(db):
    return make_user("catalog_manager", username="catmgr_user")


@pytest.fixture
def cashier(db):
    return make_user("cashier", username="cashier_user")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client_super(db, super_admin):
    """Client force-auth super_admin (bypass cookie, dùng cho test viewset)."""
    client = APIClient()
    client.force_authenticate(user=super_admin)
    return client


@pytest.fixture
def auth_client_cashier(db, cashier):
    client = APIClient()
    client.force_authenticate(user=cashier)
    return client
