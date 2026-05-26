"""Serializers cho Product.

Tách Input vs Output (HackSoft pattern):
- Input: Serializer thuần, không phải ModelSerializer — kiểm soát strict
  field nào được gửi vào, không leak model field qua reflection.
- Output: ModelSerializer cho thuận tiện, nested user info qua slim
  serializer cho list được nhẹ.
- ListItem: hẹp hơn detail — bỏ long_description, attributes (heavy)
  để list endpoint trả nhanh hơn (BR p95 < 500ms).
"""

from __future__ import annotations

import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.catalog.models import Product

User = get_user_model()

# Pattern theo SPEC AC-4
SKU_ROOT_RE = re.compile(r"^[A-Z0-9]{3,8}$")
# Slug: ascii lowercase + digit + hyphen, không leading/trailing hyphen.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# JSONB attribute key: ascii alphanumeric + underscore + hyphen.
ATTR_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class _UserSlimSerializer(serializers.ModelSerializer):
    """User minimal info cho audit display. Khi accounts app có
    User model riêng, replace bằng serializer ở đó."""

    class Meta:
        model = User
        fields = ("id", "username")


class ProductInputSerializer(serializers.Serializer):
    """Validate payload create/update. Không bind model — service tự tạo."""

    name = serializers.CharField(max_length=200)
    slug = serializers.CharField(
        max_length=220,
        required=False,
        allow_blank=True,
        default="",
    )
    sku_root = serializers.CharField(max_length=8)
    status = serializers.ChoiceField(
        choices=Product.Status.choices,
        default=Product.Status.DRAFT,
    )
    short_description = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    long_description = serializers.CharField(
        required=False, allow_blank=True, default="",
    )
    brand = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default="",
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=False),
        required=False,
        max_length=50,
        default=list,
    )
    attributes = serializers.DictField(
        required=False,
        default=dict,
    )

    def validate_sku_root(self, value: str) -> str:
        # Accept any case từ user — service normalize upper.
        if not SKU_ROOT_RE.fullmatch(value.upper()):
            raise serializers.ValidationError(
                "sku_root phải 3-8 ký tự, chỉ chữ in hoa và số (A-Z, 0-9)."
            )
        return value

    def validate_slug(self, value: str) -> str:
        # Empty → service auto-generate.
        if value and not SLUG_RE.fullmatch(value):
            raise serializers.ValidationError(
                "slug phải lowercase ascii + số, phân cách bằng dấu gạch nối."
            )
        return value

    def validate_attributes(self, value: dict) -> dict:
        for key in value:
            if not isinstance(key, str) or not ATTR_KEY_RE.fullmatch(key):
                raise serializers.ValidationError(
                    f"Key '{key}' không hợp lệ. Chỉ accept chữ/số/_/-."
                )
        return value


class ProductOutputSerializer(serializers.ModelSerializer):
    """Detail response — full fields + nested user info."""

    created_by = _UserSlimSerializer(read_only=True)
    updated_by = _UserSlimSerializer(read_only=True)
    deleted_by = _UserSlimSerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku_root",
            "status",
            "short_description",
            "long_description",
            "brand",
            "tags",
            "attributes",
            "created_at",
            "updated_at",
            "deleted_at",
            "created_by",
            "updated_by",
            "deleted_by",
        )
        read_only_fields = fields  # Output only


class ProductListItemSerializer(serializers.ModelSerializer):
    """Hẹp hơn detail — list endpoint không cần long_description/attributes
    (có thể nặng), không cần nested user (chỉ updated_at đủ context)."""

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku_root",
            "status",
            "brand",
            "tags",
            "updated_at",
            "deleted_at",
        )
        read_only_fields = fields
