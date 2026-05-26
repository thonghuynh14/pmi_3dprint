from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "entity_type", "entity_id", "actor")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "note")
    readonly_fields = (
        "id",
        "entity_type",
        "entity_id",
        "action",
        "actor",
        "actor_ip",
        "actor_user_agent",
        "changes",
        "metadata",
        "note",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False
