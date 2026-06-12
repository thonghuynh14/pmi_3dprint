"""Factories cho accounts app tests.

`RoleWithPermissionsFactory` tạo Role + gán M2M permissions theo
`ROLE_PERMISSIONS` mapping (idempotent — dùng get_or_create).

`UserWithRoleFactory.<role_code>()` shortcut tạo user với role gắn sẵn,
phục vụ test permission matrix.
"""

from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.accounts.constants import (
    PERMISSIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS,
)
from apps.accounts.models import Permission, Role, User


class PermissionFactory(DjangoModelFactory):
    class Meta:
        model = Permission
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"test:perm_{n}")
    description = factory.LazyAttribute(lambda obj: f"Test perm {obj.code}")


def make_role(role_code: str) -> Role:
    """Tạo Role với permissions đúng theo ROLE_PERMISSIONS mapping.

    Idempotent: chạy lại không lỗi (get_or_create + set).
    """
    meta = ROLE_DEFINITIONS[role_code]
    role, _ = Role.objects.get_or_create(
        code=role_code,
        defaults={"name": meta["name"], "description": meta["description"]},
    )
    perms = [
        Permission.objects.get_or_create(
            code=code, defaults={"description": PERMISSIONS[code]}
        )[0]
        for code in ROLE_PERMISSIONS[role_code]
    ]
    role.permissions.set(perms)
    return role


class UserFactory(DjangoModelFactory):
    """User generic (chưa gán role). Dùng cho test model/auth isolated."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.local")
    full_name = factory.LazyAttribute(lambda obj: obj.username.title())
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password mặc định "testpass" trừ khi extract khác."""
        if not create:
            return
        self.set_password(extracted or "testpass")
        self.save()


def make_user(role_code: str | None = None, **kwargs) -> User:
    """Tạo user với role gắn (helper top-level cho test permission matrix)."""
    role = make_role(role_code) if role_code else None
    return UserFactory(role=role, **kwargs)
