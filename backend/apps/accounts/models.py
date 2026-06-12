"""User + Role + Permission models cho RBAC.

- `User` extends AbstractBaseUser + PermissionsMixin (KHÔNG kế thừa
  `AbstractUser` để rõ ràng field, đỡ kéo theo first_name/last_name).
- `Role`: 6 role cố định trong seed (super_admin / catalog_manager /
  production_manager / channel_operator / designer / cashier).
- `Permission`: 20 code dạng `domain:action` (xem personas.md matrix).
  Tách khỏi Django built-in `auth.Permission` vì:
    1. Code chuỗi tự do (`product:create`), không gắn với contenttype.
    2. Encode dễ vào JWT claims.

ID `User` dùng `BigAutoField` (kế thừa `DEFAULT_AUTO_FIELD`) để compatible
với audit_log.actor (đã ref user qua settings.AUTH_USER_MODEL ở core).
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager


class Permission(models.Model):
    """Permission code phẳng (vd `product:create`). Không gắn contenttype."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_permissions"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    """1 role gắn N permission qua M2M. User → 1 role (FK)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_roles"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User cho 3D Printing PIM.

    KHÔNG dùng AbstractUser: clean fields, không có first_name/last_name
    (tiếng Việt thường viết "full name" 1 chuỗi).

    `role` FK nullable cho phép tạo user trước khi gán role (vd qua
    Django Admin); permission class sẽ reject 403 nếu role=None.
    """

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True)
    full_name = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Quyền truy cập Django Admin.",
    )
    # PermissionsMixin cung cấp is_superuser, groups, user_permissions

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_users"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username

    @property
    def permission_codes(self) -> list[str]:
        """List permission code từ role gắn (rỗng nếu chưa có role).

        Dùng ở JWT claims encoding (login + refresh). Cache 1 query
        qua prefetch_related khi cần list users nhiều.
        """
        if not self.role_id:
            return []
        return list(self.role.permissions.values_list("code", flat=True))
