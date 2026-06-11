"""Tests cho Variant CheckConstraint.

Defense-in-depth verification — service/serializer cũng validate, nhưng
DB constraint là last line of defense.

Wrap mỗi assertion trong transaction.atomic() để IntegrityError không
poison test transaction (default test runner wrap toàn test trong
transaction, atomic block tạo savepoint).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.skus.models import Variant

from .factories import VariantFactory


@pytest.mark.django_db
class TestCheckConstraints:
    def test_negative_base_price_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(base_price=Decimal("-1"))

    def test_negative_cost_price_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(cost_price=Decimal("-1"))

    def test_null_cost_price_ok(self):
        v = VariantFactory(cost_price=None)
        assert v.cost_price is None

    def test_zero_sequence_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(sequence_no=0)

    def test_lowercase_material_code3_raises(self):
        # Regex CHECK ``^[A-Z0-9]{2,4}$``
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(material_code3="pla")

    def test_special_char_color_code3_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(color_code3="R-D")

    def test_space_in_size_preset_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(size_preset="M L")

    def test_invalid_status_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(status="published")

    def test_sku_too_short_raises(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            VariantFactory(sku="SHORT")


@pytest.mark.django_db
class TestVariantStr:
    def test_str_returns_sku(self):
        v = VariantFactory(sku="DRAGON-PLA-RED-M-01")
        assert str(v) == "DRAGON-PLA-RED-M-01"
