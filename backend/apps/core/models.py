"""Shared base models + AuditLog.

Mọi app khác kế thừa các abstract model dưới đây để có:
- UUID PK (xem ARCHITECTURE quyết định: không leak business info, distributed-safe).
- Timestamps tự động.
- Soft delete (giữ data cho audit / undo).
- Tracking actor (created_by, updated_by, deleted_by).
- AuditLog (BR-009) ghi mọi state change quan trọng.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """UUID primary key. Lý do: không leak count, stable URL, distributed-safe."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """`created_at` + `updated_at` tự động."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet hỗ trợ soft delete + filter đã xóa / chưa xóa."""

    def delete(self) -> tuple[int, dict[str, int]]:
        # Bulk soft delete
        return self.update(deleted_at=timezone.now()), {}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()

    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager: chỉ trả về record `alive` (chưa soft-deleted).

    Dùng `Model.all_objects` để bao gồm cả record đã xóa.
    """

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """Soft delete pattern.

    delete() set `deleted_at = now()` thay vì xóa row.
    Lý do: giữ data cho audit, cho phép undo, FK reference không vỡ.
    Hard delete chỉ admin thực hiện thủ công qua management command.
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
        return 1, {}

    def hard_delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuditedModel(models.Model):
    """Track ai tạo / sửa / xóa.

    Phụ trợ AuditLog (entry chi tiết). Dùng cho mọi domain model cần audit.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        related_query_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        related_query_name="+",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        related_query_name="+",
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel, SoftDeleteModel, AuditedModel):
    """Composite base: UUID + timestamps + soft delete + audit fields.

    Dùng cho hầu hết domain model (Product, Variant, DesignFile, ...).
    """

    class Meta:
        abstract = True


class AuditLog(UUIDModel, models.Model):
    """Log mọi state change quan trọng (BR-009).

    Insert-only — không bao giờ update / delete row. Truy vấn:
        AuditLog.objects.filter(entity_type=..., entity_id=...)
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        RESTORE = "restore", "Restore"
        # Business events
        LICENSE_CHANGED = "license_changed", "License changed"
        PRICE_CHANGED = "price_changed", "Price changed"
        STOCK_CHANGED = "stock_changed", "Stock changed"
        STATUS_CHANGED = "status_changed", "Status changed"
        CHANNEL_PUBLISHED = "channel.published", "Channel published"
        CHANNEL_UNPUBLISHED = "channel.unpublished", "Channel unpublished"
        CHANNEL_SYNC_FAILED = "channel.sync_failed", "Channel sync failed"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"

    # Polymorphic FK: log mọi entity type
    entity_type = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, related_name="+"
    )
    entity_id = models.CharField(max_length=64, db_index=True)
    entity = GenericForeignKey("entity_type", "entity_id")

    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)

    # Actor
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_ip = models.GenericIPAddressField(null=True, blank=True)
    actor_user_agent = models.CharField(max_length=512, blank=True, default="")

    # Diff (JSON Patch RFC 6902 hoặc plain dict trước/sau)
    changes = models.JSONField(default=dict, blank=True)

    # Metadata bổ sung (request_id, channel, ...)
    metadata = models.JSONField(default=dict, blank=True)

    note = models.CharField(max_length=512, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "core_audit_logs"
        verbose_name = "Audit log"
        verbose_name_plural = "Audit logs"
        ordering = ("-created_at",)
        indexes: ClassVar = [
            models.Index(fields=["entity_type", "entity_id", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type} {self.entity_id} @ {self.created_at:%Y-%m-%d %H:%M}"
