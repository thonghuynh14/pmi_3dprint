"""Factories cho skus app tests.

Reuse UserFactory + ProductFactory từ catalog tests để tránh duplicate.

VariantFactory tạo Variant trực tiếp (bypass service) — chỉ dùng khi
test cần pre-existing data (model constraints, list views). Service
tests dùng ``variant_create()`` (chứ KHÔNG factory).
"""

from __future__ import annotations

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.catalog.tests.factories import ProductFactory, UserFactory  # noqa: F401
from apps.skus.models import Variant


class VariantFactory(DjangoModelFactory):
    class Meta:
        model = Variant

    product = factory.SubFactory(ProductFactory)
    sequence_no = factory.Sequence(lambda n: n + 1)
    material_name = "PLA"
    material_code3 = "PLA"
    color_name = "Red"
    color_code3 = "RED"
    size_preset = "M"
    base_price = Decimal("100000")
    cost_price = Decimal("40000")
    status = Variant.Status.DRAFT
    attributes = factory.LazyFunction(dict)

    @factory.lazy_attribute
    def sku(self) -> str:
        return (
            f"{self.product.sku_root}-{self.material_code3}-"
            f"{self.color_code3}-{self.size_preset}-{self.sequence_no:02d}"
        )

    @factory.lazy_attribute
    def name(self) -> str:
        return (
            f"{self.product.name} - {self.material_name} "
            f"{self.color_name} {self.size_preset}"
        )
