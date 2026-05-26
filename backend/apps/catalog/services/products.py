"""Write-side business logic cho Product (HackSoft service layer pattern).

Mọi mutation (create/update/soft_delete/restore) đi qua đây để:
- Validate business rules (slug/sku_root unique handled by DB partial index;
  service convert IntegrityError thành domain exception cho UX message tốt).
- Wrap @transaction.atomic.
- Ghi AuditLog (BR-009).
- Normalize input (sku_root→upper, tags→lowercase strip).

Service KHÔNG dùng ModelSerializer save — instantiate model trực tiếp để
giữ logic minh bạch và type-safe.
"""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone
from slugify import slugify

from apps.catalog.exceptions import (
    DuplicateSkuRootError,
    DuplicateSlugError,
    RestoreConflictError,
)
from apps.catalog.models import Product
from apps.core.models import AuditLog

# Field nào được audit khi create/update. Trùng với input của serializer.
_AUDIT_TRACKED_FIELDS: tuple[str, ...] = (
    "name",
    "slug",
    "sku_root",
    "status",
    "short_description",
    "long_description",
    "brand",
    "tags",
    "attributes",
)

# DB error message fragments → exception map (DB partial unique index name).
_INTEGRITY_ERROR_MAP: dict[str, type[Exception]] = {
    "catalog_products_slug_lower_alive_uq": DuplicateSlugError,
    "catalog_products_sku_root_lower_alive_uq": DuplicateSkuRootError,
}


def _audit(
    *,
    actor: Any,
    action: str,
    product: Product,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Helper ghi AuditLog cho Product mutation."""
    return AuditLog.objects.create(
        entity_type=ContentType.objects.get_for_model(Product),
        entity_id=str(product.pk),
        action=action,
        actor=actor if (actor and actor.is_authenticated) else None,
        changes=changes or {},
    )


def _generate_slug(name: str) -> str:
    """Slugify name → ascii lowercase hyphen.

    Dùng python-slugify (unidecode-backed) để convert tiếng Việt có dấu
    thành ASCII. Django built-in slugify với allow_unicode=False strip
    dấu nhưng kém với một số ký tự đặc biệt.
    """
    return slugify(name, lowercase=True, separator="-")


def _normalize_tags(tags: list[str] | None) -> list[str]:
    """Lowercase + trim + de-empty. Giữ thứ tự, không de-dup (FE đảm)."""
    return [t.strip().lower() for t in (tags or []) if t.strip()]


def _raise_for_integrity(exc: IntegrityError) -> None:
    """Convert DB partial-unique IntegrityError sang domain exception.

    Re-raise nếu không match constraint nào trong map → caller có thể
    bubble up để middleware/DRF handle (500).
    """
    msg = str(exc)
    for fragment, error_cls in _INTEGRITY_ERROR_MAP.items():
        if fragment in msg:
            raise error_cls() from exc
    raise exc


@transaction.atomic
def product_create(
    *,
    actor: Any,
    name: str,
    sku_root: str,
    slug: str = "",
    status: str = Product.Status.DRAFT,
    short_description: str = "",
    long_description: str = "",
    brand: str = "",
    tags: list[str] | None = None,
    attributes: dict[str, Any] | None = None,
) -> Product:
    """Tạo Product mới.

    Slug tự generate từ name nếu không cung cấp. sku_root được normalize
    về uppercase. Tags normalized lowercase + strip empty.

    Raises:
        DuplicateSlugError: slug đụng product alive khác (case-insensitive).
        DuplicateSkuRootError: sku_root đụng product alive khác (case-insensitive).
    """
    final_slug = slug.strip() or _generate_slug(name)

    try:
        product = Product.objects.create(
            name=name,
            slug=final_slug,
            sku_root=sku_root.upper(),
            status=status,
            short_description=short_description,
            long_description=long_description,
            brand=brand,
            tags=_normalize_tags(tags),
            attributes=attributes or {},
            created_by=actor if (actor and actor.is_authenticated) else None,
            updated_by=actor if (actor and actor.is_authenticated) else None,
        )
    except IntegrityError as exc:
        _raise_for_integrity(exc)
        raise  # unreachable, _raise_for_integrity always raises

    _audit(
        actor=actor,
        action=AuditLog.Action.CREATE,
        product=product,
        changes={
            field: [None, getattr(product, field)]
            for field in _AUDIT_TRACKED_FIELDS
        },
    )
    return product


@transaction.atomic
def product_update(*, actor: Any, product: Product, **fields: Any) -> Product:
    """Partial update — chỉ update field có giá trị mới khác giá trị cũ.

    AuditLog ghi diff dạng {field: [old, new]}.

    Raises:
        DuplicateSlugError / DuplicateSkuRootError: nếu update tạo collision.
    """
    diff: dict[str, list[Any]] = {}

    for field, new_value in fields.items():
        if field not in _AUDIT_TRACKED_FIELDS:
            # Field không cho phép update qua service (vd id, created_at).
            continue

        # Normalize input giống create.
        if field == "sku_root" and isinstance(new_value, str):
            new_value = new_value.upper()
        elif field == "tags":
            new_value = _normalize_tags(new_value)

        old_value = getattr(product, field)
        if old_value == new_value:
            continue

        setattr(product, field, new_value)
        diff[field] = [old_value, new_value]

    if not diff:
        # Nothing to save → không bump updated_at, không audit.
        return product

    product.updated_by = actor if (actor and actor.is_authenticated) else None
    try:
        product.save(
            update_fields=[*diff.keys(), "updated_at", "updated_by"],
        )
    except IntegrityError as exc:
        _raise_for_integrity(exc)
        raise

    _audit(
        actor=actor,
        action=AuditLog.Action.UPDATE,
        product=product,
        changes=diff,
    )
    return product


@transaction.atomic
def product_soft_delete(*, actor: Any, product: Product) -> None:
    """Soft delete: set deleted_at + deleted_by. Idempotent (gọi 2 lần OK).

    Audit log entry với action=delete.
    """
    if product.deleted_at is not None:
        return  # idempotent

    product.deleted_at = timezone.now()
    product.deleted_by = actor if (actor and actor.is_authenticated) else None
    product.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    _audit(actor=actor, action=AuditLog.Action.DELETE, product=product)


@transaction.atomic
def product_restore(*, actor: Any, product: Product) -> Product:
    """Khôi phục product soft-deleted (clear deleted_at).

    Idempotent: nếu product chưa deleted, trả về luôn không lỗi.

    Raises:
        RestoreConflictError: slug hoặc sku_root đã được dùng cho product
            khác alive trong lúc product này archived (SPEC EC-12).
    """
    if product.deleted_at is None:
        return product  # idempotent

    product.deleted_at = None
    product.deleted_by = None
    try:
        product.save(
            update_fields=["deleted_at", "deleted_by", "updated_at"],
        )
    except IntegrityError as exc:
        msg = str(exc)
        if any(frag in msg for frag in _INTEGRITY_ERROR_MAP):
            raise RestoreConflictError() from exc
        raise

    _audit(actor=actor, action=AuditLog.Action.RESTORE, product=product)
    return product
