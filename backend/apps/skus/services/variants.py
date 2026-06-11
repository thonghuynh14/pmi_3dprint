"""Write-side business logic cho Variant.

Pattern y hệt apps/catalog/services/products.py (HackSoft styleguide):
- Service tách khỏi view, keyword-only args.
- ``@transaction.atomic`` cho mọi write.
- AuditLog mỗi state change (BR-009).
- Convert ``IntegrityError`` → domain exception (mapping qua partial
  unique index name).

Variant-specific:
- ``variant_create`` + ``variant_bulk_create_matrix`` dùng
  ``select_for_update(Product)`` để bảo vệ race khi gen sequence_no
  (R1 risk trong ANALYSIS).
- ``variant_update`` chỉ accept field trong ``_UPDATABLE_FIELDS``; field
  immutable (material_*, color_*, size_*, sku, sequence_no, name) raise
  ``VariantFieldImmutableError`` (defense in depth — serializer cũng
  reject ở Task 1.7).
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.catalog.exceptions import ProductNotFoundError
from apps.catalog.models import Product
from apps.core.models import AuditLog
from apps.skus.exceptions import (
    BatchTooLargeError,
    DuplicateInMatrixInputError,
    DuplicateSkuError,
    DuplicateVariantComboError,
    EmptyMatrixError,
    ProductArchivedError,
    RestoreConflictError,
    VariantFieldImmutableError,
)
from apps.skus.models import Variant
from apps.skus.utils import (
    MAX_BATCH,
    compute_sku,
    compute_variant_name,
    validate_sku_length,
)

# Field nào audit khi create. variant_update tự dựng diff từ kwargs nên
# không dùng list này — chỉ initial create.
_AUDIT_TRACKED_FIELDS: tuple[str, ...] = (
    "sku",
    "sequence_no",
    "name",
    "material_name",
    "material_code3",
    "color_name",
    "color_code3",
    "size_preset",
    "base_price",
    "cost_price",
    "status",
    "attributes",
)

# Service update chỉ accept 4 field này. Mọi field khác raise.
_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"base_price", "cost_price", "status", "attributes"}
)

# DB partial unique index name → domain exception. Constraint trong
# migration 0001 (xem RunSQL operations).
_INTEGRITY_ERROR_MAP: dict[str, type[Exception]] = {
    "skus_variants_sku_lower_alive_uq": DuplicateSkuError,
    "skus_variants_combo_lower_alive_uq": DuplicateVariantComboError,
    # Race trên sequence (nếu lock không cover, vd test transaction=True).
    "skus_variants_prod_seq_alive_uq": DuplicateSkuError,
}


# =============================================================================
# Helpers
# =============================================================================
def _jsonify(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize dict thành JSON-safe primitives.

    ``AuditLog.changes`` là JSONField không config ``encoder=DjangoJSONEncoder``
    (core model dùng default → fail trên Decimal/UUID/datetime). Tránh
    đụng core model migration bằng cách stringify ở call site qua
    ``DjangoJSONEncoder`` rồi load lại.

    TODO(core): khi rảnh, thêm ``encoder=DjangoJSONEncoder`` vào
    ``AuditLog.changes`` (+ ``metadata``) để khỏi cần helper này.
    """
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _audit(
    *,
    actor: Any,
    action: str,
    variant: Variant,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Ghi 1 AuditLog cho Variant mutation."""
    return AuditLog.objects.create(
        entity_type=ContentType.objects.get_for_model(Variant),
        entity_id=str(variant.pk),
        action=action,
        actor=actor if (actor and actor.is_authenticated) else None,
        changes=_jsonify(changes or {}),
    )


def _raise_for_integrity(exc: IntegrityError) -> None:
    """Convert DB partial-unique IntegrityError → domain exception."""
    msg = str(exc)
    for fragment, error_cls in _INTEGRITY_ERROR_MAP.items():
        if fragment in msg:
            raise error_cls() from exc
    raise exc


def _lock_product(product_id: Any) -> Product:
    """``select_for_update`` Product để serialize concurrent variant_create.

    Raises:
        ProductNotFoundError: không tồn tại hoặc soft-deleted.
        ProductArchivedError: status == archived (không nhận variant mới).
    """
    try:
        product = Product.objects.select_for_update().get(pk=product_id)
    except (Product.DoesNotExist, DjangoValidationError, ValueError) as exc:
        raise ProductNotFoundError() from exc

    if product.status == Product.Status.ARCHIVED:
        raise ProductArchivedError()
    return product


def _next_sequence_no(product: Product) -> int:
    """Trả về sequence_no tiếp theo cho product.

    Dùng ``all_objects`` (gồm soft-deleted) để tránh re-use số ``NN``
    đã từng dùng — tránh nhầm lẫn khi đọc SKU.
    """
    last_seq = (
        Variant.all_objects.filter(product=product).aggregate(
            max_seq=Max("sequence_no")
        )["max_seq"]
        or 0
    )
    return last_seq + 1


# =============================================================================
# Single CRUD services
# =============================================================================
@transaction.atomic
def variant_create(
    *,
    actor: Any,
    product_id: Any,
    material_name: str,
    material_code3: str,
    color_name: str,
    color_code3: str,
    size_preset: str,
    base_price: Any,
    cost_price: Any = None,
    status: str = Variant.Status.DRAFT,
    attributes: dict[str, Any] | None = None,
) -> Variant:
    """Tạo 1 variant với SKU + sequence_no auto-gen.

    Lock Product để protect race (R1). SKU pattern v1 không có CAT3.

    Raises:
        ProductNotFoundError: product không tồn tại / soft-deleted.
        ProductArchivedError: product.status == archived.
        DuplicateVariantComboError: combo (material/color/size) đã có
            variant alive khác trên product.
        DuplicateSkuError: SKU trùng (race ngoài tầm lock).
        SkuLengthInvalidError: SKU sinh ra ngoài range 12-24 (BR-002).
    """
    product = _lock_product(product_id)

    # Normalize. size_preset giữ nguyên case (cho phép "12cm").
    material_code3 = material_code3.upper()
    color_code3 = color_code3.upper()

    next_seq = _next_sequence_no(product)

    sku = compute_sku(
        sku_root=product.sku_root,
        material_code3=material_code3,
        color_code3=color_code3,
        size_preset=size_preset,
        sequence_no=next_seq,
    )
    validate_sku_length(sku)

    name = compute_variant_name(
        product_name=product.name,
        material_name=material_name,
        color_name=color_name,
        size_preset=size_preset,
    )

    actor_user = actor if (actor and actor.is_authenticated) else None
    try:
        variant = Variant.objects.create(
            product=product,
            sku=sku,
            sequence_no=next_seq,
            material_name=material_name,
            material_code3=material_code3,
            color_name=color_name,
            color_code3=color_code3,
            size_preset=size_preset,
            name=name,
            base_price=base_price,
            cost_price=cost_price,
            status=status,
            attributes=attributes or {},
            created_by=actor_user,
            updated_by=actor_user,
        )
    except IntegrityError as exc:
        _raise_for_integrity(exc)
        raise  # unreachable

    _audit(
        actor=actor,
        action=AuditLog.Action.CREATE,
        variant=variant,
        changes={
            field: [None, getattr(variant, field)]
            for field in _AUDIT_TRACKED_FIELDS
        },
    )
    return variant


@transaction.atomic
def variant_update(*, actor: Any, variant: Variant, **fields: Any) -> Variant:
    """Partial update — chỉ accept field trong ``_UPDATABLE_FIELDS``.

    Field bất khả biến (material_*, color_*, size_preset, sku, sequence_no,
    name) sẽ raise ``VariantFieldImmutableError`` ngay khi gặp — không
    silent ignore (fail loud).

    Raises:
        VariantFieldImmutableError: caller truyền field immutable.
    """
    diff: dict[str, list[Any]] = {}
    for field, new_value in fields.items():
        if field not in _UPDATABLE_FIELDS:
            raise VariantFieldImmutableError(field=field)

        old_value = getattr(variant, field)
        if old_value == new_value:
            continue

        setattr(variant, field, new_value)
        diff[field] = [old_value, new_value]

    if not diff:
        # No-op update, không bump updated_at, không audit.
        return variant

    variant.updated_by = actor if (actor and actor.is_authenticated) else None
    variant.save(update_fields=[*diff.keys(), "updated_at", "updated_by"])

    _audit(
        actor=actor,
        action=AuditLog.Action.UPDATE,
        variant=variant,
        changes=diff,
    )
    return variant


@transaction.atomic
def variant_soft_delete(*, actor: Any, variant: Variant) -> None:
    """Soft delete (set ``deleted_at``). Idempotent (gọi 2 lần OK)."""
    if variant.deleted_at is not None:
        return

    variant.deleted_at = timezone.now()
    variant.deleted_by = actor if (actor and actor.is_authenticated) else None
    variant.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    _audit(actor=actor, action=AuditLog.Action.DELETE, variant=variant)


@transaction.atomic
def variant_restore(*, actor: Any, variant: Variant) -> Variant:
    """Khôi phục variant soft-deleted (clear ``deleted_at``).

    Idempotent: variant chưa deleted → trả luôn không lỗi.

    Raises:
        RestoreConflictError: combo / SKU đã được tái sử dụng bởi variant
            khác alive (partial unique index throws IntegrityError).
    """
    if variant.deleted_at is None:
        return variant

    variant.deleted_at = None
    variant.deleted_by = None
    try:
        variant.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
    except IntegrityError as exc:
        msg = str(exc)
        if any(frag in msg for frag in _INTEGRITY_ERROR_MAP):
            raise RestoreConflictError() from exc
        raise

    _audit(actor=actor, action=AuditLog.Action.RESTORE, variant=variant)
    return variant


# =============================================================================
# Matrix bulk service
# =============================================================================
@transaction.atomic
def variant_bulk_create_matrix(
    *,
    actor: Any,
    product_id: Any,
    materials: list[dict[str, str]],
    colors: list[dict[str, str]],
    sizes: list[str],
    base_price: Any,
    cost_price: Any = None,
    status: str = Variant.Status.DRAFT,
) -> list[Variant]:
    """Tạo N×M×P variants atomic (all-or-nothing).

    Quy trình:
    1. Validate ≥1 value/axis (``EmptyMatrixError`` nếu thiếu).
    2. Validate ``total ≤ MAX_BATCH`` (``BatchTooLargeError`` nếu vượt).
    3. Detect duplicate trong input matrix (case-insensitive).
    4. ``select_for_update(Product)`` để protect sequence race.
    5. Pre-check combo overlap với variants alive trong DB; nếu có,
       raise ``DuplicateVariantComboError`` với list ``conflicts``.
    6. ``bulk_create`` + ``bulk_create`` audit log.

    Args:
        materials: ``[{"name": "PLA", "code3": "PLA"}, ...]``
        colors: ``[{"name": "Red", "code3": "RED"}, ...]``
        sizes: ``["S", "M", "L"]``

    Returns:
        Danh sách Variant đã tạo (PK đã set qua UUID default).
    """
    if not materials or not colors or not sizes:
        raise EmptyMatrixError()

    total = len(materials) * len(colors) * len(sizes)
    if total > MAX_BATCH:
        raise BatchTooLargeError(requested=total, max_allowed=MAX_BATCH)

    # Detect duplicate input axis values (case-insensitive theo DB index).
    mat_codes_lower = [m["code3"].lower() for m in materials]
    col_codes_lower = [c["code3"].lower() for c in colors]
    size_lower = [s.lower() for s in sizes]
    if (
        len(set(mat_codes_lower)) != len(mat_codes_lower)
        or len(set(col_codes_lower)) != len(col_codes_lower)
        or len(set(size_lower)) != len(size_lower)
    ):
        raise DuplicateInMatrixInputError()

    product = _lock_product(product_id)

    # Last sequence_no — qua all_objects để tránh re-use NN từ deleted variants.
    last_seq = (
        Variant.all_objects.filter(product=product).aggregate(
            max_seq=Max("sequence_no")
        )["max_seq"]
        or 0
    )

    # Pre-check combos đã có trên DB (chỉ alive). DB partial unique sẽ
    # catch race ở bulk_create, nhưng pre-check cho error message tốt hơn.
    existing_combos = {
        (m.lower(), c.lower(), s.lower())
        for (m, c, s) in Variant.objects.filter(product=product).values_list(
            "material_code3", "color_code3", "size_preset"
        )
    }

    actor_user = actor if (actor and actor.is_authenticated) else None
    variants_to_create: list[Variant] = []
    conflicts: list[dict[str, str]] = []

    for material in materials:
        mat_code = material["code3"].upper()
        for color in colors:
            col_code = color["code3"].upper()
            for size in sizes:
                combo_lower = (mat_code.lower(), col_code.lower(), size.lower())
                if combo_lower in existing_combos:
                    conflicts.append(
                        {
                            "material_code3": mat_code,
                            "color_code3": col_code,
                            "size_preset": size,
                        }
                    )
                    continue

                last_seq += 1
                sku = compute_sku(
                    sku_root=product.sku_root,
                    material_code3=mat_code,
                    color_code3=col_code,
                    size_preset=size,
                    sequence_no=last_seq,
                )
                validate_sku_length(sku)

                name = compute_variant_name(
                    product_name=product.name,
                    material_name=material["name"],
                    color_name=color["name"],
                    size_preset=size,
                )

                variants_to_create.append(
                    Variant(
                        product=product,
                        sku=sku,
                        sequence_no=last_seq,
                        material_name=material["name"],
                        material_code3=mat_code,
                        color_name=color["name"],
                        color_code3=col_code,
                        size_preset=size,
                        name=name,
                        base_price=base_price,
                        cost_price=cost_price,
                        status=status,
                        attributes={},
                        created_by=actor_user,
                        updated_by=actor_user,
                    )
                )

    if conflicts:
        # Override detail để FE thấy danh sách combo đụng.
        exc = DuplicateVariantComboError()
        exc.detail = {
            "detail": "Một hoặc nhiều combo đã tồn tại alive trên product này.",
            "conflicts": conflicts,
        }
        raise exc

    try:
        Variant.objects.bulk_create(variants_to_create)
    except IntegrityError as exc:
        _raise_for_integrity(exc)
        raise

    # bulk_create với UUID PK default → instances đã có pk set.
    content_type = ContentType.objects.get_for_model(Variant)
    audit_entries = [
        AuditLog(
            entity_type=content_type,
            entity_id=str(v.pk),
            action=AuditLog.Action.CREATE,
            actor=actor_user,
            changes=_jsonify(
                {field: [None, getattr(v, field)] for field in _AUDIT_TRACKED_FIELDS}
            ),
        )
        for v in variants_to_create
    ]
    AuditLog.objects.bulk_create(audit_entries)

    return variants_to_create
