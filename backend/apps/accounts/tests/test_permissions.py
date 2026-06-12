"""Tests cho HasPermission + ActionPermission classes."""

from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.accounts.permissions import ActionPermission, HasPermission
from apps.accounts.tests.factories import make_user


@pytest.fixture
def factory():
    return APIRequestFactory()


def _make_drf_request(factory, user, jwt_claims=None):
    """Helper: tạo DRF Request đã gắn user + optional _jwt_claims."""
    from rest_framework.request import Request

    request = factory.get("/")
    drf = Request(request)
    drf.user = user
    if jwt_claims is not None:
        drf._jwt_claims = jwt_claims
    return drf


@pytest.mark.django_db
class TestHasPermission:
    def test_denies_anonymous(self, factory):
        from django.contrib.auth.models import AnonymousUser

        request = _make_drf_request(factory, AnonymousUser())
        perm = HasPermission.with_code("product:read")()
        assert perm.has_permission(request, None) is False

    def test_allows_when_jwt_claims_have_code(self, factory):
        user = make_user("catalog_manager")
        request = _make_drf_request(
            factory, user, jwt_claims={"permissions": ["product:read"]}
        )
        perm = HasPermission.with_code("product:read")()
        assert perm.has_permission(request, None) is True

    def test_denies_when_jwt_claims_lack_code(self, factory):
        user = make_user("cashier")
        request = _make_drf_request(
            factory, user, jwt_claims={"permissions": ["order:read"]}
        )
        perm = HasPermission.with_code("product:create")()
        assert perm.has_permission(request, None) is False

    def test_fallback_to_db_when_no_jwt_claims(self, factory):
        """force_authenticate không set _jwt_claims → fallback user.permission_codes."""
        user = make_user("catalog_manager")
        request = _make_drf_request(factory, user, jwt_claims=None)
        perm = HasPermission.with_code("product:create")()
        assert perm.has_permission(request, None) is True


@pytest.mark.django_db
class TestActionPermission:
    class _FakeView:
        action_permission_map = {
            "list": "product:read",
            "create": "product:create",
        }
        action = "list"

    def test_uses_view_action_map(self, factory):
        user = make_user("catalog_manager")
        request = _make_drf_request(
            factory, user, jwt_claims={"permissions": ["product:read"]}
        )
        view = self._FakeView()
        assert ActionPermission().has_permission(request, view) is True

    def test_denies_when_action_lacks_required_perm(self, factory):
        user = make_user("cashier")
        request = _make_drf_request(
            factory, user, jwt_claims={"permissions": ["order:read"]}
        )
        view = self._FakeView()
        view.action = "create"  # cần product:create
        assert ActionPermission().has_permission(request, view) is False

    def test_denies_unknown_action_without_default(self, factory):
        user = make_user("super_admin")
        request = _make_drf_request(
            factory, user, jwt_claims={"permissions": ["product:read"]}
        )
        view = self._FakeView()
        view.action = "unknown_action"
        assert ActionPermission().has_permission(request, view) is False
