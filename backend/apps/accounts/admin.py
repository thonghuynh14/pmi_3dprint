"""Django Admin cho User + Role + Permission.

Super admin quản lý user/role qua đây (UI web defer sang feature sau).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.accounts.models import Permission, Role, User


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "created_at")
    search_fields = ("code", "description")
    ordering = ("code",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "permission_count", "updated_at")
    search_fields = ("code", "name")
    filter_horizontal = ("permissions",)
    ordering = ("code",)

    @admin.display(description="# permissions")
    def permission_count(self, obj: Role) -> int:
        return obj.permissions.count()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Tuỳ biến Django BaseUserAdmin cho field hiện có."""

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("username", "email", "full_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "full_name")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profile", {"fields": ("email", "full_name")}),
        ("RBAC", {"fields": ("role",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "role"),
            },
        ),
    )
    readonly_fields = ("date_joined", "last_login")
