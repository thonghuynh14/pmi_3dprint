"""Serializers cho Variant.

Tách 5 serializer theo HackSoft pattern:
- ``VariantInputSerializer`` — payload ``POST /variants/`` (single create).
- ``VariantUpdateSerializer`` — payload ``PATCH``. Chỉ 4 field
  (base_price/cost_price/status/attributes); reject immutable trong
  ``validate()`` → 400 fail loud (SPEC AC9).
- ``VariantMatrixInputSerializer`` — payload matrix endpoint với 3 axis.
- ``VariantOutputSerializer`` — detail response, ``ModelSerializer``.
- ``VariantListItemSerializer`` — hẹp hơn cho list endpoint.

Input không dùng ``ModelSerializer`` → kiểm soát strict field nào nhận.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.skus.exceptions import VariantFieldImmutableError
from apps.skus.models import Variant
from apps.skus.utils import MAX_BATCH

User = get_user_model()

# code3: 2-4 uppercase alphanumeric. Lowercase chấp nhận khi gửi — serializer
# upper-case trong validate_<field>.
CODE3_RE = re.compile(r"^[A-Z0-9]{2,4}$")
# size_preset: 1-8 alphanumeric (cho phép "12cm", giữ nguyên case).
SIZE_PRESET_RE = re.compile(r"^[A-Za-z0-9]{1,8}$")

# Field immutable sau create. Service cũng enforce (defense in depth)
# nhưng serializer reject sớm để response 400 thay vì xuống service.
_IMMUTABLE_FIELDS = frozenset(
    {
        "sku",
        "sequence_no",
        "name",
        "product_id",
        "material_name",
        "material_code3",
        "color_name",
        "color_code3",
        "size_preset",
    }
)


class _UserSlimSerializer(serializers.ModelSerializer):
    """User minimal info cho audit display."""

    class Meta:
        model = User
        fields = ("id", "username")


# =============================================================================
# Input — single create
# =============================================================================
class VariantInputSerializer(serializers.Serializer):
    """Validate payload ``POST /skus/variants/``. Service normalize + tạo."""

    product_id = serializers.UUIDField()
    material_name = serializers.CharField(max_length=64, min_length=1)
    material_code3 = serializers.CharField(max_length=4)
    color_name = serializers.CharField(max_length=64, min_length=1)
    color_code3 = serializers.CharField(max_length=4)
    size_preset = serializers.CharField(max_length=8)
    base_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0")
    )
    cost_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(
        choices=Variant.Status.choices, default=Variant.Status.DRAFT
    )
    attributes = serializers.DictField(required=False, default=dict)

    def validate_material_code3(self, value: str) -> str:
        upper = value.upper()
        if not CODE3_RE.fullmatch(upper):
            raise serializers.ValidationError(
                "material_code3 phải 2-4 ký tự chữ in hoa hoặc số (A-Z, 0-9)."
            )
        return upper

    def validate_color_code3(self, value: str) -> str:
        upper = value.upper()
        if not CODE3_RE.fullmatch(upper):
            raise serializers.ValidationError(
                "color_code3 phải 2-4 ký tự chữ in hoa hoặc số (A-Z, 0-9)."
            )
        return upper

    def validate_size_preset(self, value: str) -> str:
        if not SIZE_PRESET_RE.fullmatch(value):
            raise serializers.ValidationError(
                "size_preset phải 1-8 ký tự alphanumeric."
            )
        return value


# =============================================================================
# Input — partial update
# =============================================================================
class VariantUpdateSerializer(serializers.Serializer):
    """Partial update. Chỉ 4 field mutable.

    Nếu user gửi field immutable → raise ``VariantFieldImmutableError``
    (return 400 fail loud, không silent ignore — SPEC AC9).
    """

    base_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    cost_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(
        choices=Variant.Status.choices, required=False
    )
    attributes = serializers.DictField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # initial_data luôn có (DRF set khi `data=` truyền vào).
        forbidden = set(self.initial_data.keys()) & _IMMUTABLE_FIELDS
        if forbidden:
            # Pick deterministic: sorted để test reproducible.
            raise VariantFieldImmutableError(field=sorted(forbidden)[0])
        return attrs


# =============================================================================
# Input — matrix bulk
# =============================================================================
class _AxisEntrySerializer(serializers.Serializer):
    """1 entry trong matrix axis: ``{"name": ..., "code3": ...}``."""

    name = serializers.CharField(max_length=64, min_length=1)
    code3 = serializers.CharField(max_length=4)

    def validate_code3(self, value: str) -> str:
        upper = value.upper()
        if not CODE3_RE.fullmatch(upper):
            raise serializers.ValidationError(
                "code3 phải 2-4 ký tự chữ in hoa hoặc số (A-Z, 0-9)."
            )
        return upper


class VariantMatrixInputSerializer(serializers.Serializer):
    """Validate payload matrix endpoint.

    Service check ``EmptyMatrix`` / ``BatchTooLarge`` / ``DuplicateInMatrix``
    (case-insensitive) — serializer chỉ validate format + tổng size.
    """

    materials = _AxisEntrySerializer(many=True)
    colors = _AxisEntrySerializer(many=True)
    sizes = serializers.ListField(
        child=serializers.CharField(max_length=8),
    )
    base_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0")
    )
    cost_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(
        choices=Variant.Status.choices, default=Variant.Status.DRAFT
    )

    def validate_materials(self, value):
        if len(value) < 1:
            raise serializers.ValidationError(
                "Cần ít nhất 1 material."
            )
        return value

    def validate_colors(self, value):
        if len(value) < 1:
            raise serializers.ValidationError(
                "Cần ít nhất 1 color."
            )
        return value

    def validate_sizes(self, value: list[str]) -> list[str]:
        if len(value) < 1:
            raise serializers.ValidationError(
                "Cần ít nhất 1 size."
            )
        for size in value:
            if not SIZE_PRESET_RE.fullmatch(size):
                raise serializers.ValidationError(
                    f"size '{size}' không hợp lệ (cần 1-8 alphanumeric)."
                )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        total = (
            len(attrs["materials"]) * len(attrs["colors"]) * len(attrs["sizes"])
        )
        if total > MAX_BATCH:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        f"Tổng variants ({total}) vượt giới hạn "
                        f"{MAX_BATCH}/batch."
                    ],
                }
            )
        return attrs


# =============================================================================
# Output / List
# =============================================================================
class VariantOutputSerializer(serializers.ModelSerializer):
    """Detail response — full fields + nested user info."""

    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    created_by = _UserSlimSerializer(read_only=True)
    updated_by = _UserSlimSerializer(read_only=True)
    deleted_by = _UserSlimSerializer(read_only=True)

    class Meta:
        model = Variant
        fields = (
            "id",
            "sku",
            "sequence_no",
            "name",
            "product_id",
            "product_name",
            "material_name",
            "material_code3",
            "color_name",
            "color_code3",
            "size_preset",
            "base_price",
            "cost_price",
            "status",
            "attributes",
            "created_at",
            "updated_at",
            "deleted_at",
            "created_by",
            "updated_by",
            "deleted_by",
        )
        read_only_fields = fields


class VariantListItemSerializer(serializers.ModelSerializer):
    """Hẹp hơn detail — list endpoint không cần long fields / nested user."""

    class Meta:
        model = Variant
        fields = (
            "id",
            "sku",
            "name",
            "sequence_no",
            "material_code3",
            "color_code3",
            "size_preset",
            "base_price",
            "status",
            "updated_at",
            "deleted_at",
        )
        read_only_fields = fields
