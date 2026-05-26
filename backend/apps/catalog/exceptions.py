"""Domain exceptions cho catalog app.

Tất cả extend `APIException` → DRF tự xử lý thành HTTP response với
field `detail` + `code`. ViewSet không cần try/except riêng.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException


class ProductError(APIException):
    """Base cho mọi lỗi business của Product."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Product error"
    default_code = "product_error"


class ProductNotFoundError(ProductError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Product không tồn tại."
    default_code = "product_not_found"


class DuplicateSlugError(ProductError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Slug đã tồn tại trong hệ thống."
    default_code = "duplicate_slug"


class DuplicateSkuRootError(ProductError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Mã sku_root đã tồn tại (case-insensitive)."
    default_code = "duplicate_sku_root"


class RestoreConflictError(ProductError):
    """Khi restore product, slug hoặc sku_root đã được tái sử dụng trong
    lúc archived (xem SPEC EC-12)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "Không thể khôi phục: slug hoặc sku_root đã được dùng cho product khác."
    )
    default_code = "restore_conflict"
