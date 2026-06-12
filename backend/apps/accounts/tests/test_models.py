"""Tests cho User + Role + Permission models."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.accounts.models import Permission, Role, User
from apps.accounts.tests.factories import (
    PermissionFactory,
    UserFactory,
    make_role,
    make_user,
)


@pytest.mark.django_db
class TestUserModel:
    def test_str_returns_username(self):
        u = UserFactory(username="alice")
        assert str(u) == "alice"

    def test_username_unique(self):
        """Factory dùng get_or_create cho user → test trực tiếp qua model."""
        UserFactory(username="dup")
        with pytest.raises(IntegrityError):
            User.objects.create(username="dup", email="other@x.local")

    def test_permission_codes_empty_when_no_role(self):
        u = UserFactory(role=None)
        assert u.permission_codes == []

    def test_permission_codes_returns_role_perms(self):
        u = make_user("catalog_manager")
        codes = u.permission_codes
        assert "product:create" in codes
        assert "channel:publish" not in codes  # catalog manager không có

    def test_create_superuser(self):
        u = User.objects.create_superuser(
            username="root", email="root@x.local", password="pass"
        )
        assert u.is_superuser is True
        assert u.is_staff is True
        assert u.check_password("pass") is True

    def test_create_user_without_username_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(username="", password="pass")


@pytest.mark.django_db
class TestPermissionModel:
    def test_code_unique(self):
        """Factory get_or_create → test qua model trực tiếp."""
        PermissionFactory(code="x:y")
        with pytest.raises(IntegrityError):
            Permission.objects.create(code="x:y")


@pytest.mark.django_db
class TestRoleModel:
    def test_role_permissions_m2m(self):
        role = make_role("cashier")
        codes = list(role.permissions.values_list("code", flat=True))
        assert "order:create_pos" in codes
        assert "product:create" not in codes

    def test_role_idempotent(self):
        r1 = make_role("super_admin")
        r2 = make_role("super_admin")
        assert r1.id == r2.id
        assert Role.objects.filter(code="super_admin").count() == 1

    def test_full_seed_creates_all_24_perms(self):
        """make_role gọi tới Permission.get_or_create cho từng code."""
        make_role("super_admin")  # super_admin có full 24 perms
        assert Permission.objects.count() == 24
