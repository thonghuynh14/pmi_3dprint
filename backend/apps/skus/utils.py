"""Helper functions cho variant logic.

- ``compute_sku``: gen SKU theo pattern v1 (bỏ CAT3 vì Category chưa có).
- ``validate_sku_length``: enforce BR-002 length 12-24.
- ``compute_variant_name``: auto-gen name từ product + axis.
- Constants: ``SKU_LEN_MIN`` / ``SKU_LEN_MAX`` / ``MAX_BATCH``.
"""

from __future__ import annotations

from .exceptions import SkuLengthInvalidError

# BR-002: SKU length 12-24.
SKU_LEN_MIN = 12
SKU_LEN_MAX = 24

# Cap matrix bulk creation — tránh DB stress + UI freeze (R2 risk).
MAX_BATCH = 100


def compute_sku(
    *,
    sku_root: str,
    material_code3: str,
    color_code3: str,
    size_preset: str,
    sequence_no: int,
) -> str:
    """Sinh SKU theo pattern v1: ``<sku_root>-<MAT3>-<COL3>-<SIZE>-<NN>``.

    CAT3 defer tới khi có Category feature (ANALYSIS R4).
    Sequence zero-padded 2 chữ số (``01``, ``02``, ..., ``99``).

    Args được expect đã normalize (code3 uppercase, sku_root uppercase).
    Caller chịu trách nhiệm normalize trước.
    """
    return (
        f"{sku_root}-{material_code3}-{color_code3}-"
        f"{size_preset}-{sequence_no:02d}"
    )


def validate_sku_length(sku: str) -> None:
    """Raise ``SkuLengthInvalidError`` nếu sku ngoài BR-002 range (12-24).

    Defense in depth — model CheckConstraint cũng enforce, nhưng raise
    sớm ở service để có HTTP 400 thay vì IntegrityError 500.
    """
    length = len(sku)
    if not (SKU_LEN_MIN <= length <= SKU_LEN_MAX):
        raise SkuLengthInvalidError(sku=sku, length=length)


def compute_variant_name(
    *,
    product_name: str,
    material_name: str,
    color_name: str,
    size_preset: str,
) -> str:
    """Auto-gen variant name: ``{product} - {material} {color} {size}``.

    Tối đa 200 ký tự (model max_length). Caller (service / serializer)
    nên validate trước khi tạo nếu các input quá dài.
    """
    return (
        f"{product_name} - {material_name} {color_name} {size_preset}"
    )
