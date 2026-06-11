"""Domain exceptions cho skus app.

Pattern y hệt apps/catalog/exceptions.py: extend APIException, set
status_code + default_detail + default_code. DRF tự xử lý thành HTTP
response — ViewSet không cần try/except riêng.

Một số exception (BatchTooLarge, SkuLengthInvalid, VariantFieldImmutable)
cần payload thêm để FE hiển thị chính xác → override __init__ để compose
detail dạng dict.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException


class VariantError(APIException):
    """Base cho mọi lỗi business của Variant."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Variant error"
    default_code = "variant_error"


class VariantNotFoundError(VariantError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Variant không tồn tại."
    default_code = "variant_not_found"


class DuplicateSkuError(VariantError):
    """SKU trùng (case-insensitive). Race ngoài tầm select_for_update."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "SKU đã tồn tại (case-insensitive)."
    default_code = "duplicate_sku"


class DuplicateVariantComboError(VariantError):
    """Combo (material_code3, color_code3, size_preset) đã tồn tại cho
    product này (case-insensitive)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Variant đã tồn tại với material + color + size này trên product."
    )
    default_code = "duplicate_variant_combo"


class DuplicateInMatrixInputError(VariantError):
    """User submit matrix với 2 axis value trùng nhau (case-insensitive)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Input matrix có giá trị axis trùng "
        "(kiểm tra material_code3 / color_code3 / size)."
    )
    default_code = "duplicate_in_matrix_input"


class BatchTooLargeError(VariantError):
    """Matrix yêu cầu tạo > MAX_BATCH variants/lần."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "variant_batch_too_large"

    def __init__(self, requested: int, max_allowed: int) -> None:
        super().__init__(
            detail={
                "detail": (
                    f"Tổng variants ({requested}) vượt giới hạn "
                    f"{max_allowed}/batch."
                ),
                "max": max_allowed,
                "requested": requested,
            }
        )


class EmptyMatrixError(VariantError):
    """Matrix có ít nhất 1 axis = 0 value."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Matrix rỗng: cần ít nhất 1 giá trị cho mỗi axis "
        "(materials, colors, sizes)."
    )
    default_code = "empty_matrix"


class ProductArchivedError(VariantError):
    """Không tạo variant trên product đang archived."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Không thể tạo variant cho product đang ở trạng thái 'archived'."
    )
    default_code = "product_archived"


class SkuLengthInvalidError(VariantError):
    """SKU sinh ra ngoài range BR-002 (12-24 chars)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "sku_length_invalid"

    def __init__(self, sku: str, length: int) -> None:
        super().__init__(
            detail={
                "detail": (
                    f"SKU '{sku}' có độ dài {length} ký tự, "
                    "ngoài range cho phép (12-24)."
                ),
                "sku": sku,
                "length": length,
            }
        )


class VariantFieldImmutableError(VariantError):
    """User cố sửa field bất khả biến (material_*/color_*/size_*/sku/
    sequence_no/name)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "variant_field_immutable"

    def __init__(self, field: str) -> None:
        super().__init__(
            detail={
                "detail": (
                    f"Field '{field}' không thể sửa sau khi variant được tạo."
                ),
                "field": field,
            }
        )


class RestoreConflictError(VariantError):
    """Khi restore variant, combo đã được tái sử dụng bởi variant khác
    active (xem SPEC EC-12 tương đương Product CRUD)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Không thể khôi phục: combo (material/color/size) đã có variant "
        "active khác trên cùng product."
    )
    default_code = "restore_conflict"
