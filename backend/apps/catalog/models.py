"""Catalog models.

Hiện tại chỉ có Product. Category, Brand, AttributeDefinition sẽ thêm
trong các feature riêng (xem docs/features/_template/...).

Product là entity gốc; mọi feature catalog phía sau (Variant, ChannelListing,
BOM, POC, DesignFile binding) đều có FK trỏ Product. Vì vậy schema này là
foundation — đổi sau sẽ tốn migration đau.
"""

from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import BaseModel


class Product(BaseModel):
    """Sản phẩm gốc (parent của variants).

    `sku_root` là 6 ký tự compact identifier để variant SKU sau dùng
    pattern `[CAT3]-[PROD6]-[MAT3]-[COLOR3]-[SIZE]-[NN]`. Lần này không
    có Category nên `[CAT3]` defer.

    `attributes` JSONB chứa thuộc tính dynamic chung của product (vd:
    estimated_weight, scale_ratio, recommended_age). Variant override
    qua attributes riêng. GIN index hỗ trợ filter containment.

    `tags` là text[] dùng cho phân loại nhẹ (vd: ["figure", "dragon",
    "fantasy"]). Lowercase + trim trước khi lưu ở serializer.

    Tham chiếu DESIGN.md §"Database changes" cho DDL đầy đủ.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, allow_unicode=False)
    sku_root = models.CharField(max_length=8)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    short_description = models.TextField(blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    brand = models.CharField(max_length=100, blank=True, default="")
    tags = ArrayField(
        models.CharField(max_length=64),
        default=list,
        blank=True,
        size=50,
    )
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "catalog_products"
        ordering = ("-updated_at",)
        verbose_name = "Product"
        verbose_name_plural = "Products"
        constraints = [
            # sku_root: 3-8 chữ in hoa hoặc số. Validate cả ở serializer
            # (UX message tốt hơn) — đây là defense in depth ở DB.
            models.CheckConstraint(
                condition=models.Q(sku_root__regex=r"^[A-Z0-9]{3,8}$"),
                name="catalog_products_sku_root_format",
            ),
            # status chỉ accept giá trị enum (defense in depth — Django
            # choices không enforce ở DB).
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "active", "archived"]),
                name="catalog_products_status_choices",
            ),
        ]
        indexes = [
            # Sort default updated_at desc — phục vụ list endpoint.
            models.Index(
                fields=["-updated_at"],
                name="catalog_products_updated_idx",
            ),
            # Filter status nhanh khi list (chỉ row alive).
            models.Index(
                fields=["status"],
                condition=models.Q(deleted_at__isnull=True),
                name="catalog_products_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku_root})"
