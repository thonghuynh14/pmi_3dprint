"""Read-side queries cho Product.

Selectors chỉ đọc, không write. Mọi write delegate sang services/.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.catalog.exceptions import ProductNotFoundError
from apps.catalog.models import Product


def get_product(
    *,
    product_id: uuid.UUID | str,
    include_deleted: bool = False,
) -> Product:
    """Trả về 1 Product theo id.

    Args:
        product_id: UUID hoặc string UUID.
        include_deleted: nếu True, dùng `all_objects` (kể cả soft-deleted).

    Raises:
        ProductNotFoundError: nếu product không tồn tại trong scope đã chọn.
    """
    manager = Product.all_objects if include_deleted else Product.objects
    try:
        return (
            manager
            .select_related("created_by", "updated_by", "deleted_by")
            .get(pk=product_id)
        )
    except (Product.DoesNotExist, ValueError, ValidationError) as exc:
        # ValidationError: UUIDField raise khi string không parse UUID được.
        # ValueError: defensive cho case khác.
        raise ProductNotFoundError() from exc


def list_products(
    *,
    search: str = "",
    status: str | None = None,
    show_archived: bool = False,
    ordering: str = "-updated_at",
) -> QuerySet[Product]:
    """List products có filter + search + ordering.

    Args:
        search: case-insensitive contains match trên name HOẶC sku_root.
            Trỏ vào GIN trgm index (migration 0001) cho perf.
        status: filter exact status. None = không filter.
        show_archived: nếu True, dùng `all_objects` (gồm cả soft-deleted).
        ordering: Django ordering string, default "-updated_at".

    Returns:
        QuerySet[Product] lazy — caller pagination/serialize sau.
    """
    qs = Product.all_objects.all() if show_archived else Product.objects.all()

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sku_root__icontains=search))

    if status:
        qs = qs.filter(status=status)

    return qs.order_by(ordering)
