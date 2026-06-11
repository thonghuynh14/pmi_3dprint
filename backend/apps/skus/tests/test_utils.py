"""Tests cho apps.skus.utils.

Cover BR-002 SKU length boundaries + compute helpers.
"""

from __future__ import annotations

import pytest

from apps.skus.exceptions import SkuLengthInvalidError
from apps.skus.utils import (
    MAX_BATCH,
    SKU_LEN_MAX,
    SKU_LEN_MIN,
    compute_sku,
    compute_variant_name,
    validate_sku_length,
)


class TestComputeSku:
    def test_format_matches_v1_pattern(self):
        sku = compute_sku(
            sku_root="DRAGON",
            material_code3="PLA",
            color_code3="RED",
            size_preset="M",
            sequence_no=1,
        )
        assert sku == "DRAGON-PLA-RED-M-01"

    def test_sequence_zero_padded_2_digits(self):
        sku = compute_sku(
            sku_root="ABC", material_code3="PLA", color_code3="RED",
            size_preset="M", sequence_no=7,
        )
        assert sku.endswith("-07")

    def test_sequence_99_not_padded_extra(self):
        sku = compute_sku(
            sku_root="ABC", material_code3="PLA", color_code3="RED",
            size_preset="M", sequence_no=99,
        )
        assert sku.endswith("-99")

    def test_sequence_above_99_uses_more_digits(self):
        # ``:02d`` chỉ pad min 2 digit — không cap. 100 → "-100".
        sku = compute_sku(
            sku_root="ABC", material_code3="PLA", color_code3="RED",
            size_preset="M", sequence_no=100,
        )
        assert sku.endswith("-100")


class TestValidateSkuLength:
    """BR-002: length ∈ [12, 24]."""

    @pytest.mark.parametrize("length", [12, 13, 18, 23, 24])
    def test_in_range_passes(self, length):
        validate_sku_length("A" * length)  # no raise

    @pytest.mark.parametrize("length", [0, 1, 5, 11])
    def test_below_min_raises(self, length):
        with pytest.raises(SkuLengthInvalidError):
            validate_sku_length("A" * length)

    @pytest.mark.parametrize("length", [25, 30, 100])
    def test_above_max_raises(self, length):
        with pytest.raises(SkuLengthInvalidError):
            validate_sku_length("A" * length)

    def test_error_carries_sku_and_length(self):
        with pytest.raises(SkuLengthInvalidError) as exc_info:
            validate_sku_length("SHORT")
        assert exc_info.value.detail["sku"] == "SHORT"
        # DRF wrap value trong ErrorDetail (extends str) → so sánh dạng int.
        assert int(exc_info.value.detail["length"]) == 5


class TestComputeVariantName:
    def test_format(self):
        name = compute_variant_name(
            product_name="Dragon Figure",
            material_name="PLA",
            color_name="Red",
            size_preset="M",
        )
        assert name == "Dragon Figure - PLA Red M"

    def test_handles_unicode(self):
        name = compute_variant_name(
            product_name="Mô hình rồng",
            material_name="PLA",
            color_name="Đỏ",
            size_preset="M",
        )
        assert name == "Mô hình rồng - PLA Đỏ M"


class TestConstants:
    def test_sku_range(self):
        assert SKU_LEN_MIN == 12
        assert SKU_LEN_MAX == 24

    def test_max_batch(self):
        assert MAX_BATCH == 100
