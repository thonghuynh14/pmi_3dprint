"""Custom manager cho User model.

`BaseUserManager` cung cấp `normalize_email`. Override `create_user` /
`create_superuser` để dùng `username` làm USERNAME_FIELD (giữ flow giống
Django default, không đổi sang email-based để tránh thay đổi `smoke`).
"""

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Manager cho `accounts.User`. Không dùng `use_in_migrations=True`
    để tránh Django auto-call trong migration RunPython — seed riêng qua
    management command."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("Username là bắt buộc.")
        email = self.normalize_email(email) if email else ""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser phải có is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser phải có is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)
