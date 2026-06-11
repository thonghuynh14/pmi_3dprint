"""Tests cho services/variants.py.

Cover CRUD single + matrix bulk + race condition + audit log + edge cases.
SPEC ACs referenced inline.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.catalog.exceptions import ProductNotFoundError
from apps.catalog.models import Product
from apps.catalog.tests.factories import ProductFactory, UserFactory
from apps.core.models import AuditLog
from apps.skus.exceptions import (
    BatchTooLargeError,
    DuplicateInMatrixInputError,
    DuplicateVariantComboError,
    EmptyMatrixError,
    ProductArchivedError,
    RestoreConflictError,
    VariantFieldImmutableError,
)
from apps.skus.models import Variant
from apps.skus.services.variants import (
    variant_bulk_create_matrix,
    variant_create,
    variant_restore,
    variant_soft_delete,
    variant_update,
)
from apps.skus.utils import MAX_BATCH


def _audits_for(variant: Variant):
    return AuditLog.objects.filter(
        entity_type=ContentType.objects.get_for_model(Variant),
        entity_id=str(variant.pk),
    ).order_by("created_at")


def _basic_axes() -> dict:
    """Min payload cho variant_create."""
    return {
        "material_name": "PLA",
        "material_code3": "PLA",
        "color_name": "Red",
        "color_code3": "RED",
        "size_preset": "M",
        "base_price": Decimal("150000"),
    }


# =============================================================================
# variant_create
# =============================================================================
@pytest.mark.django_db
class TestVariantCreate:
    def test_creates_with_minimal_fields(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        assert v.pk is not None
        assert v.sku == f"{product.sku_root}-PLA-RED-M-01"
        assert v.sequence_no == 1
        assert v.status == Variant.Status.DRAFT
        assert v.created_by == user
        assert v.updated_by == user

    def test_normalizes_code3_to_upper(self, user, product):
        v = variant_create(
            actor=user, product_id=product.id,
            material_name="PLA", material_code3="pla",
            color_name="Red", color_code3="red",
            size_preset="M", base_price=Decimal("100"),
        )
        assert v.material_code3 == "PLA"
        assert v.color_code3 == "RED"
        assert "PLA-RED" in v.sku

    def test_size_preset_preserves_case(self, user, product):
        v = variant_create(
            actor=user, product_id=product.id,
            material_name="PLA", material_code3="PLA",
            color_name="Red", color_code3="RED",
            size_preset="12cm", base_price=Decimal("100"),
        )
        assert v.size_preset == "12cm"

    def test_auto_gen_name(self, user, product):
        product.name = "Dragon Figure"
        product.save()
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        assert v.name == "Dragon Figure - PLA Red M"

    def test_sku_in_BR002_length_range(self, user):
        """SPEC AC8: length ∈ [12, 24] với boundary inputs."""
        product = ProductFactory(sku_root="ABCDEFGH", status=Product.Status.ACTIVE)
        v = variant_create(
            actor=user, product_id=product.id,
            material_name="PETG", material_code3="PETG",
            color_name="Orange", color_code3="ORG",
            size_preset="XL", base_price=Decimal("100"),
        )
        # ABCDEFGH(8) + - + PETG(4) + - + ORG(3) + - + XL(2) + - + 01(2) = 22
        assert 12 <= len(v.sku) <= 24

    def test_audit_log_created(self, user, product):
        """SPEC AC1 + BR-009."""
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        logs = list(_audits_for(v))
        assert len(logs) == 1
        log = logs[0]
        assert log.action == AuditLog.Action.CREATE
        assert log.actor == user
        assert log.changes["sku"] == [None, v.sku]
        assert log.changes["sequence_no"] == [None, 1]

    def test_product_archived_blocks(self, user):
        """SPEC AC5."""
        archived = ProductFactory(status=Product.Status.ARCHIVED)
        with pytest.raises(ProductArchivedError):
            variant_create(actor=user, product_id=archived.id, **_basic_axes())

    def test_product_not_found_raises(self, user):
        with pytest.raises(ProductNotFoundError):
            variant_create(
                actor=user,
                product_id="00000000-0000-0000-0000-000000000000",
                **_basic_axes(),
            )

    def test_product_soft_deleted_raises(self, user, product):
        product.delete()
        with pytest.raises(ProductNotFoundError):
            variant_create(actor=user, product_id=product.id, **_basic_axes())

    def test_duplicate_combo_raises_409(self, user, product):
        """SPEC AC6."""
        variant_create(actor=user, product_id=product.id, **_basic_axes())
        with pytest.raises(DuplicateVariantComboError):
            variant_create(actor=user, product_id=product.id, **_basic_axes())

    def test_duplicate_combo_case_insensitive(self, user, product):
        variant_create(actor=user, product_id=product.id, **_basic_axes())
        with pytest.raises(DuplicateVariantComboError):
            # Lowercase axis — DB partial unique trên LOWER() bắt được.
            variant_create(
                actor=user, product_id=product.id,
                material_name="PLA", material_code3="pla",
                color_name="Red", color_code3="red",
                size_preset="m", base_price=Decimal("100"),
            )

    def test_sequence_increments_per_product(self, user, product):
        v1 = variant_create(actor=user, product_id=product.id, **_basic_axes())
        v2 = variant_create(
            actor=user, product_id=product.id,
            material_name="PLA", material_code3="PLA",
            color_name="Blue", color_code3="BLU",
            size_preset="M", base_price=Decimal("100"),
        )
        assert v1.sequence_no == 1
        assert v2.sequence_no == 2

    def test_sequence_skips_deleted(self, user, product):
        """Sequence_no đếm cả deleted để tránh re-use NN."""
        v1 = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v1)
        v2 = variant_create(
            actor=user, product_id=product.id,
            material_name="PLA", material_code3="PLA",
            color_name="Blue", color_code3="BLU",
            size_preset="M", base_price=Decimal("100"),
        )
        assert v2.sequence_no == 2  # NOT 1, dù v1 đã deleted

    def test_actor_none_is_ok(self, product):
        v = variant_create(actor=None, product_id=product.id, **_basic_axes())
        assert v.created_by is None


# =============================================================================
# variant_update
# =============================================================================
@pytest.mark.django_db
class TestVariantUpdate:
    def test_updates_base_price(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        updated = variant_update(actor=user, variant=v, base_price=Decimal("200000"))
        assert updated.base_price == Decimal("200000.00")

    def test_updates_status(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        updated = variant_update(actor=user, variant=v, status=Variant.Status.ACTIVE)
        assert updated.status == Variant.Status.ACTIVE

    def test_audit_logs_diff(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        v.refresh_from_db()  # canonical Decimal precision
        variant_update(actor=user, variant=v, base_price=Decimal("200000"))
        update_logs = _audits_for(v).filter(action=AuditLog.Action.UPDATE)
        assert update_logs.count() == 1
        diff = update_logs.first().changes["base_price"]
        assert Decimal(diff[0]) == Decimal("150000")
        assert Decimal(diff[1]) == Decimal("200000")

    def test_no_audit_when_no_change(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        v.refresh_from_db()
        variant_update(actor=user, variant=v, base_price=v.base_price)
        update_logs = _audits_for(v).filter(action=AuditLog.Action.UPDATE)
        assert update_logs.count() == 0

    @pytest.mark.parametrize("field,value", [
        ("sku", "X"),
        ("sequence_no", 99),
        ("name", "fake"),
        ("product_id", "00000000-0000-0000-0000-000000000000"),
        ("material_name", "ABS"),
        ("material_code3", "ABS"),
        ("color_name", "Blue"),
        ("color_code3", "BLU"),
        ("size_preset", "L"),
    ])
    def test_immutable_field_raises(self, user, product, field, value):
        """SPEC AC9."""
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        with pytest.raises(VariantFieldImmutableError) as exc_info:
            variant_update(actor=user, variant=v, **{field: value})
        assert exc_info.value.detail["field"] == field


# =============================================================================
# variant_soft_delete + variant_restore
# =============================================================================
@pytest.mark.django_db
class TestVariantSoftDelete:
    def test_sets_deleted_at(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v)
        v.refresh_from_db()
        assert v.deleted_at is not None
        assert v.deleted_by == user

    def test_idempotent(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v)
        first_delete = v.deleted_at
        variant_soft_delete(actor=user, variant=v)
        v.refresh_from_db()
        assert v.deleted_at == first_delete
        assert _audits_for(v).filter(action=AuditLog.Action.DELETE).count() == 1

    def test_audit_logged(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v)
        assert _audits_for(v).filter(action=AuditLog.Action.DELETE).count() == 1


@pytest.mark.django_db
class TestVariantRestore:
    def test_clears_deleted_at(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v)
        restored = variant_restore(actor=user, variant=v)
        assert restored.deleted_at is None
        assert restored.deleted_by is None

    def test_idempotent_when_not_deleted(self, user, product):
        v = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_restore(actor=user, variant=v)
        assert _audits_for(v).filter(action=AuditLog.Action.RESTORE).count() == 0

    def test_conflict_when_combo_taken(self, user, product):
        """Combo đã được tái sử dụng bởi variant khác alive → 409."""
        v1 = variant_create(actor=user, product_id=product.id, **_basic_axes())
        variant_soft_delete(actor=user, variant=v1)
        # v2 cùng combo — DB partial unique cho phép vì v1 deleted.
        variant_create(actor=user, product_id=product.id, **_basic_axes())
        with pytest.raises(RestoreConflictError):
            variant_restore(actor=user, variant=v1)


# =============================================================================
# variant_bulk_create_matrix
# =============================================================================
@pytest.mark.django_db
class TestVariantBulkCreateMatrix:
    def test_creates_NxMxP(self, user, product):
        """SPEC AC2: 2×3×3 = 18 variants."""
        created = variant_bulk_create_matrix(
            actor=user, product_id=product.id,
            materials=[
                {"name": "PLA", "code3": "PLA"},
                {"name": "PETG", "code3": "PET"},
            ],
            colors=[
                {"name": "Red", "code3": "RED"},
                {"name": "Blue", "code3": "BLU"},
                {"name": "Green", "code3": "GRN"},
            ],
            sizes=["S", "M", "L"],
            base_price=Decimal("150000"),
        )
        assert len(created) == 18
        assert len({v.sku for v in created}) == 18
        assert sorted(v.sequence_no for v in created) == list(range(1, 19))

    def test_sequence_continues_from_existing(self, user, product):
        variant_create(
            actor=user, product_id=product.id,
            material_name="ABS", material_code3="ABS",
            color_name="Black", color_code3="BLK",
            size_preset="XL", base_price=Decimal("100"),
        )
        created = variant_bulk_create_matrix(
            actor=user, product_id=product.id,
            materials=[
                {"name": "PLA", "code3": "PLA"},
                {"name": "PETG", "code3": "PET"},
            ],
            colors=[{"name": "Red", "code3": "RED"}],
            sizes=["M"],
            base_price=Decimal("100"),
        )
        assert sorted(v.sequence_no for v in created) == [2, 3]

    def test_empty_axis_raises(self, user, product):
        with pytest.raises(EmptyMatrixError):
            variant_bulk_create_matrix(
                actor=user, product_id=product.id,
                materials=[], colors=[{"name": "Red", "code3": "RED"}],
                sizes=["M"], base_price=Decimal("100"),
            )

    def test_batch_too_large_raises(self, user, product):
        """SPEC AC4: total > 100."""
        with pytest.raises(BatchTooLargeError) as exc_info:
            variant_bulk_create_matrix(
                actor=user, product_id=product.id,
                materials=[
                    {"name": f"M{i}", "code3": f"M{i:02d}"} for i in range(11)
                ],
                colors=[
                    {"name": f"C{i}", "code3": f"C{i:02d}"} for i in range(11)
                ],
                sizes=["M"],
                base_price=Decimal("100"),
            )
        # DRF wrap value trong ErrorDetail (extends str) → so sánh dạng str.
        assert int(exc_info.value.detail["requested"]) == 121
        assert int(exc_info.value.detail["max"]) == MAX_BATCH

    def test_duplicate_in_input_raises(self, user, product):
        """SPEC AC7."""
        with pytest.raises(DuplicateInMatrixInputError):
            variant_bulk_create_matrix(
                actor=user, product_id=product.id,
                materials=[
                    {"name": "PLA", "code3": "PLA"},
                    {"name": "PLA copy", "code3": "pla"},  # case-insensitive dup
                ],
                colors=[{"name": "Red", "code3": "RED"}],
                sizes=["M"],
                base_price=Decimal("100"),
            )

    def test_combo_overlap_with_db_raises_with_list(self, user, product):
        """SPEC AC6 trong context matrix: detail có ``conflicts`` list."""
        variant_create(actor=user, product_id=product.id, **_basic_axes())
        with pytest.raises(DuplicateVariantComboError) as exc_info:
            variant_bulk_create_matrix(
                actor=user, product_id=product.id,
                materials=[{"name": "PLA", "code3": "PLA"}],
                colors=[
                    {"name": "Red", "code3": "RED"},
                    {"name": "Blue", "code3": "BLU"},
                ],
                sizes=["M"],
                base_price=Decimal("100"),
            )
        assert "conflicts" in exc_info.value.detail
        assert len(exc_info.value.detail["conflicts"]) == 1
        assert exc_info.value.detail["conflicts"][0]["material_code3"] == "PLA"

    def test_combo_overlap_atomic_no_partial_insert(self, user, product):
        variant_create(actor=user, product_id=product.id, **_basic_axes())
        initial = Variant.objects.filter(product=product).count()
        with pytest.raises(DuplicateVariantComboError):
            variant_bulk_create_matrix(
                actor=user, product_id=product.id,
                materials=[{"name": "PLA", "code3": "PLA"}],
                colors=[
                    {"name": "Red", "code3": "RED"},
                    {"name": "Blue", "code3": "BLU"},
                ],
                sizes=["M"],
                base_price=Decimal("100"),
            )
        assert Variant.objects.filter(product=product).count() == initial

    def test_product_archived_blocks(self, user):
        archived = ProductFactory(status=Product.Status.ARCHIVED)
        with pytest.raises(ProductArchivedError):
            variant_bulk_create_matrix(
                actor=user, product_id=archived.id,
                materials=[{"name": "PLA", "code3": "PLA"}],
                colors=[{"name": "Red", "code3": "RED"}],
                sizes=["M"],
                base_price=Decimal("100"),
            )

    def test_audit_log_per_variant(self, user, product):
        created = variant_bulk_create_matrix(
            actor=user, product_id=product.id,
            materials=[{"name": "PLA", "code3": "PLA"}],
            colors=[
                {"name": "Red", "code3": "RED"},
                {"name": "Blue", "code3": "BLU"},
            ],
            sizes=["M"],
            base_price=Decimal("100"),
        )
        for v in created:
            assert (
                _audits_for(v).filter(action=AuditLog.Action.CREATE).count() == 1
            )


# =============================================================================
# Race condition (SPEC AC3)
# =============================================================================
@pytest.mark.django_db(transaction=True)
class TestVariantCreateRaceCondition:
    """5 thread concurrent → 5 SKU unique nhờ select_for_update(Product)."""

    def test_concurrent_creates_unique_sequence(self):
        import threading

        from django.db import connections

        product = ProductFactory(status=Product.Status.ACTIVE)
        user = UserFactory()
        results: list[Variant] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def attempt(i: int) -> None:
            try:
                v = variant_create(
                    actor=user, product_id=product.id,
                    material_name="PLA", material_code3="PLA",
                    color_name=f"C{i}", color_code3=f"C{i:02d}",
                    size_preset="M", base_price=Decimal("100"),
                )
                with lock:
                    results.append(v)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append(e)
            finally:
                # Mỗi thread phải đóng connection của mình (Django thread-local).
                connections.close_all()

        threads = [
            threading.Thread(target=attempt, args=(i,)) for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"unexpected errors: {errors}"
        assert len(results) == 5
        assert sorted(v.sequence_no for v in results) == [1, 2, 3, 4, 5]
        assert len({v.sku for v in results}) == 5
