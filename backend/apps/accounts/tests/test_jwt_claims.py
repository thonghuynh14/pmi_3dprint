"""Tests cho CustomRefreshToken (encode role + permissions claims)."""

from __future__ import annotations

import pytest

from apps.accounts.jwt_utils import CustomRefreshToken
from apps.accounts.tests.factories import make_user


@pytest.mark.django_db
class TestCustomRefreshToken:
    def test_refresh_claims_contain_role_permissions(self):
        u = make_user("super_admin")
        rt = CustomRefreshToken.for_user(u)
        assert rt["role"] == "super_admin"
        assert rt["username"] == u.username
        assert isinstance(rt["permissions"], list)
        assert "user:manage" in rt["permissions"]

    def test_access_token_inherits_claims(self):
        u = make_user("catalog_manager")
        at = CustomRefreshToken.for_user(u).access_token
        assert at["role"] == "catalog_manager"
        assert "product:create" in at["permissions"]
        assert "channel:publish" not in at["permissions"]

    def test_user_without_role_has_empty_permissions(self):
        u = make_user(None, username="solo")
        rt = CustomRefreshToken.for_user(u)
        assert rt["role"] is None
        assert rt["permissions"] == []

    @pytest.mark.parametrize(
        "role_code,expected_count",
        [
            ("super_admin", 24),
            ("catalog_manager", 12),
            ("production_manager", 7),
            ("channel_operator", 5),
            ("designer", 4),
            ("cashier", 4),
        ],
    )
    def test_permission_count_per_role(self, role_code, expected_count):
        u = make_user(role_code)
        rt = CustomRefreshToken.for_user(u)
        assert len(rt["permissions"]) == expected_count
