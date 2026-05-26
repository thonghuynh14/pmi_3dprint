"""Django Admin cho catalog app.

Super Admin dùng để CRUD trực tiếp khi cần (bypass FE). Override
`get_queryset()` để hiển thị cả row soft-deleted (default manager
exclude `deleted_at IS NOT NULL`).
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone

from apps.catalog.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku_root",
        "status",
        "brand",
        "updated_at",
        "deleted_at",
    )
    list_filter = ("status", "deleted_at")
    search_fields = ("name", "sku_root", "slug")
    ordering = ("-updated_at",)
    prepopulated_fields = {"slug": ("name",)}

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "deleted_by",
    )

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "sku_root", "status"),
        }),
        ("Description", {
            "fields": ("short_description", "long_description", "brand"),
            "classes": ("collapse",),
        }),
        ("Structured data", {
            "fields": ("tags", "attributes"),
            "classes": ("collapse",),
        }),
        ("Audit", {
            "fields": (
                "id",
                ("created_at", "created_by"),
                ("updated_at", "updated_by"),
                ("deleted_at", "deleted_by"),
            ),
            "classes": ("collapse",),
        }),
    )

    actions = ("soft_delete_selected", "restore_selected")

    def get_queryset(self, request):
        # Admin nhìn được cả row soft-deleted để restore.
        return Product.all_objects.get_queryset()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Soft-delete các Product đã chọn")
    def soft_delete_selected(self, request, queryset):
        alive = queryset.filter(deleted_at__isnull=True)
        count = alive.update(
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )
        self.message_user(
            request,
            f"Đã soft-delete {count} product.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Khôi phục Product đã chọn (clear deleted_at)")
    def restore_selected(self, request, queryset):
        deleted = queryset.filter(deleted_at__isnull=False)
        count = deleted.update(deleted_at=None, deleted_by=None)
        self.message_user(
            request,
            f"Đã khôi phục {count} product.",
            level=messages.SUCCESS,
        )
