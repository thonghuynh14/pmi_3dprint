"""SKU models.

Variant = phiên bản bán được, gắn 1:N với Product. Mỗi Variant đại diện
1 tổ hợp axis cụ thể (material × color × size_preset) → 1 SKU duy nhất.

SKU pattern v1: `<product.sku_root>-<MAT3>-<COLOR3>-<SIZE>-<NN>`, length
12-22, ∈ BR-002 range (12-24). CAT3 defer tới khi có Category feature.

License check (BR-003), design_file FK, cost calc (BR-005) defer khỏi v1
— sẽ làm cùng Design Files + Material feature.

Tham chiếu docs/features/02-variant-crud/DESIGN.md.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Variant(BaseModel):
    """Variant — phiên bản bán được của Product.

    `sequence_no` là counter per-product, dùng phần `NN` trong SKU.
    Bảo vệ race bằng `select_for_update(Product)` trong service create.

    `material_code3` / `color_code3` (uppercase alphanumeric 2-4) đi vào
    SKU pattern; `material_name` / `color_name` (free string) cho hiển
    thị. Tách 2 cột để tránh suy ngược "Polylactic Acid" → "POL" (mong
    muốn "PLA").

    `name` auto-gen `"{product.name} - {material_name} {color_name}
    {size_preset}"`. DB column (không compose ở UI) để search được.

    Field IMMUTABLE sau create (service update reject 400): sku,
    sequence_no, name, material_*, color_*, size_preset. Chỉ
    base_price / cost_price / status / attributes editable.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="variants",
        related_query_name="variant",
    )
    sku = models.CharField(max_length=24)
    sequence_no = models.PositiveIntegerField()

    # 3 axis — free name + code3 (cho SKU pattern).
    material_name = models.CharField(max_length=64)
    material_code3 = models.CharField(max_length=4)
    color_name = models.CharField(max_length=64)
    color_code3 = models.CharField(max_length=4)
    size_preset = models.CharField(max_length=8)

    # Auto-gen từ product.name + axis.
    name = models.CharField(max_length=200)

    # Pricing (VND, money-safe Decimal).
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # JSONB cho thuộc tính phụ (finish, food_safe, ...). GIN index ở migration.
    attributes = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "skus_variants"
        ordering = ("product", "sequence_no")
        verbose_name = "Variant"
        verbose_name_plural = "Variants"
        constraints = [
            # Money non-negative (defense in depth — serializer validate ở FE).
            models.CheckConstraint(
                condition=models.Q(base_price__gte=0),
                name="skus_variants_base_price_nonneg",
            ),
            models.CheckConstraint(
                condition=models.Q(cost_price__isnull=True)
                | models.Q(cost_price__gte=0),
                name="skus_variants_cost_price_nonneg",
            ),
            # sequence_no >= 1.
            models.CheckConstraint(
                condition=models.Q(sequence_no__gte=1),
                name="skus_variants_sequence_positive",
            ),
            # Status enum (Django choices không enforce ở DB).
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "active", "archived"]),
                name="skus_variants_status_choices",
            ),
            # code3 format: 2-4 uppercase alphanumeric.
            models.CheckConstraint(
                condition=models.Q(material_code3__regex=r"^[A-Z0-9]{2,4}$"),
                name="skus_variants_material_code3_format",
            ),
            models.CheckConstraint(
                condition=models.Q(color_code3__regex=r"^[A-Z0-9]{2,4}$"),
                name="skus_variants_color_code3_format",
            ),
            # size_preset: 1-8 alphanumeric (cho phép "12cm").
            models.CheckConstraint(
                condition=models.Q(size_preset__regex=r"^[A-Za-z0-9]{1,8}$"),
                name="skus_variants_size_preset_format",
            ),
            # BR-002 SKU length 12-24 (defense in depth — service validate trước).
            models.CheckConstraint(
                condition=models.Q(sku__regex=r"^.{12,24}$"),
                name="skus_variants_sku_length",
            ),
        ]
        indexes = [
            # Default ordering helper (product + sequence_no).
            models.Index(
                fields=["product", "sequence_no"],
                name="skus_variants_prod_seq_idx",
            ),
            # Filter status nhanh trên row alive (partial index).
            models.Index(
                fields=["status"],
                condition=models.Q(deleted_at__isnull=True),
                name="skus_variants_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.sku
