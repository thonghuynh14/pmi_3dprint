"""Django Admin cho skus app.

Super Admin dùng để CRUD/inspect khi cần. Field axis + sku + name là
read-only (immutable post-create — phù hợp với service rule).
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone

from apps.skus.models import Variant


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "product",
        "status",
        "base_price",
        "sequence_no",
        "updated_at",
        "deleted_at",
    )
    list_filter = ("status", "deleted_at", "material_code3")
    search_fields = ("sku", "name", "product__name", "product__sku_root")
    ordering = ("product", "sequence_no")

    readonly_fields = (
        "id",
        "sku",
        "sequence_no",
        "name",
        "product",
        "material_name",
        "material_code3",
        "color_name",
        "color_code3",
        "size_preset",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "deleted_by",
    )

    fieldsets = (
        (None, {
            "fields": ("product", "sku", "sequence_no", "name", "status"),
        }),
        ("Axes (immutable)", {
            "fields": (
                ("material_name", "material_code3"),
                ("color_name", "color_code3"),
                "size_preset",
            ),
        }),
        ("Pricing", {
            "fields": ("base_price", "cost_price"),
        }),
        ("Structured data", {
            "fields": ("attributes",),
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
        # Admin xem cả row soft-deleted để có thể restore.
        return Variant.all_objects.get_queryset().select_related("product")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Soft-delete các Variant đã chọn")
    def soft_delete_selected(self, request, queryset):
        alive = queryset.filter(deleted_at__isnull=True)
        count = alive.update(
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )
        self.message_user(
            request,
            f"Đã soft-delete {count} variant.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Khôi phục Variant đã chọn (clear deleted_at)")
    def restore_selected(self, request, queryset):
        deleted = queryset.filter(deleted_at__isnull=False)
        count = deleted.update(deleted_at=None, deleted_by=None)
        self.message_user(
            request,
            f"Đã khôi phục {count} variant.",
            level=messages.SUCCESS,
        )
