"""Tests cho services/products.py.

Cover: create, update, soft_delete, restore + audit log + edge cases.
"""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.catalog.exceptions import (
    DuplicateSkuRootError,
    DuplicateSlugError,
    RestoreConflictError,
)
from apps.catalog.models import Product
from apps.catalog.services.products import (
    product_create,
    product_restore,
    product_soft_delete,
    product_update,
)
from apps.core.models import AuditLog

from .factories import ProductFactory, UserFactory


def _audit_logs_for(product: Product):
    return AuditLog.objects.filter(
        entity_type=ContentType.objects.get_for_model(Product),
        entity_id=str(product.pk),
    ).order_by("created_at")


# ---------------------------------------------------------------------------
# product_create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductCreate:
    def test_create_with_minimal_fields_succeeds(self, user):
        product = product_create(
            actor=user,
            name="Dragon Figure",
            sku_root="DRAGON",
        )
        assert product.pk is not None
        assert product.name == "Dragon Figure"
        assert product.sku_root == "DRAGON"
        assert product.status == Product.Status.DRAFT
        assert product.created_by == user
        assert product.updated_by == user

    def test_create_auto_generates_slug_from_name(self, user):
        product = product_create(
            actor=user,
            name="Dragon Figure v2",
            sku_root="DRGV2",
        )
        assert product.slug == "dragon-figure-v2"

    def test_create_with_unicode_name_generates_ascii_slug(self, user):
        product = product_create(
            actor=user,
            name="Mô hình rồng đỏ",
            sku_root="MHRONG",
        )
        # python-slugify (unidecode) convert dấu → ascii.
        assert product.slug == "mo-hinh-rong-do"

    def test_create_with_explicit_slug_uses_it(self, user):
        product = product_create(
            actor=user,
            name="Whatever",
            sku_root="ABC",
            slug="custom-slug",
        )
        assert product.slug == "custom-slug"

    def test_create_normalizes_sku_root_to_uppercase(self, user):
        # sku_root regex chỉ chấp uppercase → service phải upper trước
        # khi insert, không để user phải tự nhớ.
        product = product_create(
            actor=user,
            name="X",
            sku_root="abc123",
        )
        assert product.sku_root == "ABC123"

    def test_create_normalizes_tags_lowercase_strip_empty(self, user):
        product = product_create(
            actor=user,
            name="X",
            sku_root="X01",
            tags=["  Figure ", "DRAGON", "", "  "],
        )
        assert product.tags == ["figure", "dragon"]

    def test_create_with_attributes_jsonb(self, user):
        product = product_create(
            actor=user,
            name="X",
            sku_root="X02",
            attributes={"scale": "1:10", "weight_g": 120},
        )
        assert product.attributes == {"scale": "1:10", "weight_g": 120}

    def test_create_duplicate_slug_raises_duplicate_slug_error(self, user):
        product_create(actor=user, name="A", sku_root="AAA", slug="dragon")
        with pytest.raises(DuplicateSlugError):
            product_create(actor=user, name="B", sku_root="BBB", slug="dragon")

    def test_create_duplicate_slug_case_insensitive_raises(self, user):
        product_create(actor=user, name="A", sku_root="AAA", slug="dragon")
        with pytest.raises(DuplicateSlugError):
            product_create(actor=user, name="B", sku_root="BBB", slug="DRAGON")

    def test_create_duplicate_sku_root_case_insensitive_raises(self, user):
        product_create(actor=user, name="A", sku_root="DRAGON")
        with pytest.raises(DuplicateSkuRootError):
            # input lowercase, service upper-case → đụng "DRAGON".
            product_create(actor=user, name="B", sku_root="dragon")

    def test_create_duplicate_slug_allowed_after_soft_delete(self, user):
        # SPEC AC-8 edge: cho phép reuse slug sau soft delete.
        first = product_create(actor=user, name="A", sku_root="AAA", slug="dragon")
        product_soft_delete(actor=user, product=first)
        second = product_create(actor=user, name="B", sku_root="BBB", slug="dragon")
        assert second.pk != first.pk

    def test_create_writes_audit_log_with_create_action(self, user):
        product = product_create(actor=user, name="X", sku_root="XXX")
        logs = _audit_logs_for(product)
        assert logs.count() == 1
        log = logs.first()
        assert log.action == AuditLog.Action.CREATE
        assert log.actor == user
        # changes record full snapshot: {field: [None, new]}
        assert log.changes["name"] == [None, "X"]
        assert log.changes["sku_root"] == [None, "XXX"]


# ---------------------------------------------------------------------------
# product_update
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductUpdate:
    def test_update_only_changed_fields_audited(self, user):
        product = product_create(
            actor=user, name="Old", sku_root="ABC",
            short_description="orig",
        )
        # touch updated_at trước để nhận diện diff log
        updated = product_update(
            actor=user, product=product, name="New",
        )
        assert updated.name == "New"
        assert updated.short_description == "orig"  # không đổi

        logs = _audit_logs_for(product).filter(action=AuditLog.Action.UPDATE)
        assert logs.count() == 1
        log = logs.first()
        # Diff chỉ chứa name, không có short_description
        assert "name" in log.changes
        assert "short_description" not in log.changes
        assert log.changes["name"] == ["Old", "New"]

    def test_update_no_change_returns_same_product_no_audit(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        # Lấy số log create = 1
        logs_before = _audit_logs_for(product).count()

        # Update với cùng giá trị (no-op)
        product_update(actor=user, product=product, name="X")

        logs_after = _audit_logs_for(product).count()
        assert logs_after == logs_before  # không tăng

    def test_update_ignores_unknown_field(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        # Field không tracked (vd "id") bị skip — không lỗi, không audit
        product_update(actor=user, product=product, some_random_field="value")
        assert _audit_logs_for(product).filter(
            action=AuditLog.Action.UPDATE
        ).count() == 0

    def test_update_normalizes_sku_root_uppercase(self, user):
        product = product_create(actor=user, name="X", sku_root="OLD")
        updated = product_update(actor=user, product=product, sku_root="new123")
        assert updated.sku_root == "NEW123"

    def test_update_normalizes_tags(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        updated = product_update(
            actor=user, product=product, tags=["  Dragon  ", "FIGURE"],
        )
        assert updated.tags == ["dragon", "figure"]

    def test_update_duplicate_slug_raises(self, user):
        product_create(actor=user, name="A", sku_root="AAA", slug="taken")
        other = product_create(actor=user, name="B", sku_root="BBB", slug="free")
        with pytest.raises(DuplicateSlugError):
            product_update(actor=user, product=other, slug="taken")

    def test_update_status_to_active_succeeds(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_update(actor=user, product=product, status=Product.Status.ACTIVE)
        product.refresh_from_db()
        assert product.status == Product.Status.ACTIVE


# ---------------------------------------------------------------------------
# product_soft_delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductSoftDelete:
    def test_soft_delete_sets_deleted_at(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        product.refresh_from_db()
        assert product.deleted_at is not None
        assert product.deleted_by == user

    def test_soft_delete_excludes_from_default_query(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        assert not Product.objects.filter(pk=product.pk).exists()
        assert Product.all_objects.filter(pk=product.pk).exists()

    def test_soft_delete_idempotent(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        first_deleted_at = product.deleted_at

        # Gọi lần 2 — không lỗi, không bump deleted_at, không thêm audit.
        product_soft_delete(actor=user, product=product)
        product.refresh_from_db()
        assert product.deleted_at == first_deleted_at

        delete_logs = _audit_logs_for(product).filter(action=AuditLog.Action.DELETE)
        assert delete_logs.count() == 1

    def test_soft_delete_writes_audit_log(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        delete_logs = _audit_logs_for(product).filter(action=AuditLog.Action.DELETE)
        assert delete_logs.count() == 1
        assert delete_logs.first().actor == user


# ---------------------------------------------------------------------------
# product_restore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductRestore:
    def test_restore_clears_deleted_at(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        assert product.deleted_at is not None

        restored = product_restore(actor=user, product=product)
        assert restored.deleted_at is None
        assert restored.deleted_by is None
        # Đã quay lại default manager.
        assert Product.objects.filter(pk=product.pk).exists()

    def test_restore_writes_audit_log(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        product_soft_delete(actor=user, product=product)
        product_restore(actor=user, product=product)
        restore_logs = _audit_logs_for(product).filter(
            action=AuditLog.Action.RESTORE
        )
        assert restore_logs.count() == 1

    def test_restore_idempotent_when_not_deleted(self, user):
        product = product_create(actor=user, name="X", sku_root="X01")
        # Chưa soft delete → restore là no-op
        result = product_restore(actor=user, product=product)
        assert result.pk == product.pk
        assert _audit_logs_for(product).filter(
            action=AuditLog.Action.RESTORE
        ).count() == 0

    def test_restore_conflict_when_slug_reused(self, user):
        """SPEC EC-12: slug đã được tái sử dụng → RestoreConflictError."""
        first = product_create(actor=user, name="A", sku_root="AAA", slug="shared")
        product_soft_delete(actor=user, product=first)
        # Tạo product mới với slug giống → OK vì partial unique
        product_create(actor=user, name="B", sku_root="BBB", slug="shared")

        with pytest.raises(RestoreConflictError):
            product_restore(actor=user, product=first)

    def test_restore_conflict_when_sku_root_reused(self, user):
        first = product_create(actor=user, name="A", sku_root="DRAGON")
        product_soft_delete(actor=user, product=first)
        product_create(actor=user, name="B", sku_root="DRAGON")

        with pytest.raises(RestoreConflictError):
            product_restore(actor=user, product=first)
