"""Read-side queries cho Variant.

Selectors chỉ đọc, không write. Mọi mutation delegate sang services/.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.skus.exceptions import VariantNotFoundError
from apps.skus.models import Variant


def get_variant(
    *,
    variant_id: uuid.UUID | str,
    include_deleted: bool = False,
) -> Variant:
    """Lấy 1 Variant theo id.

    Args:
        variant_id: UUID hoặc string UUID.
        include_deleted: nếu True dùng ``all_objects`` (gồm soft-deleted).

    Raises:
        VariantNotFoundError: không tồn tại trong scope đã chọn, hoặc
            id không parse được UUID.
    """
    manager = Variant.all_objects if include_deleted else Variant.objects
    try:
        return (
            manager.select_related(
                "product", "created_by", "updated_by", "deleted_by"
            ).get(pk=variant_id)
        )
    except (Variant.DoesNotExist, ValueError, ValidationError) as exc:
        # ValidationError: UUIDField raise khi string không parse UUID.
        raise VariantNotFoundError() from exc


def list_variants(
    *,
    product_id: uuid.UUID | str | None = None,
    search: str = "",
    status: str | None = None,
    show_archived: bool = False,
    ordering: str = "sequence_no",
) -> QuerySet[Variant]:
    """List variants với filter + search + ordering.

    Args:
        product_id: filter theo product. ``None`` = không filter.
        search: case-insensitive contains trên ``sku`` HOẶC ``name``.
            Tận dụng GIN trgm indexes (migration 0001) cho perf.
        status: filter exact status. ``None`` = không filter.
        show_archived: nếu True dùng ``all_objects`` (gồm soft-deleted).
        ordering: Django ordering string, default ``"sequence_no"``.

    Returns:
        QuerySet[Variant] lazy với ``.select_related("product")`` để
        tránh N+1 khi serializer truy cập ``product.name``.
    """
    qs = (Variant.all_objects if show_archived else Variant.objects).all()
    qs = qs.select_related("product")

    if product_id is not None:
        qs = qs.filter(product_id=product_id)

    if search:
        qs = qs.filter(Q(sku__icontains=search) | Q(name__icontains=search))

    if status:
        qs = qs.filter(status=status)

    return qs.order_by(ordering)
