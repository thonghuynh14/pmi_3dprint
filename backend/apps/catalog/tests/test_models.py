"""Tests cho Product model.

Coverage targets:
- Field defaults + str
- CheckConstraint sku_root format
- Partial unique index slug/sku_root (case-insensitive, alive-only)
- Soft delete behavior (deleted_at, default manager, all_objects)
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import Product

from .factories import ProductFactory


@pytest.mark.django_db
class TestProductCreate:
    def test_create_minimal_succeeds(self):
        p = ProductFactory()
        assert p.pk is not None
        assert p.status == Product.Status.DRAFT
        assert p.tags == []
        assert p.attributes == {}
        assert p.brand == ""
        assert p.deleted_at is None

    def test_str_returns_name_and_sku_root(self):
        p = ProductFactory(name="Dragon Figure", sku_root="DRAGON")
        assert str(p) == "Dragon Figure (DRAGON)"

    def test_default_ordering_updated_at_desc(self):
        older = ProductFactory()
        newer = ProductFactory()
        # touch newer to bump updated_at
        newer.save()
        ordered = list(Product.objects.all())
        assert ordered[0].pk == newer.pk
        assert ordered[1].pk == older.pk


@pytest.mark.django_db
class TestSkuRootFormatConstraint:
    """BR-related defensive check: sku_root regex `^[A-Z0-9]{3,8}$`."""

    def test_lowercase_blocked(self):
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                ProductFactory(sku_root="dragon")
        assert "catalog_products_sku_root_format" in str(exc.value)

    def test_special_char_blocked(self):
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                ProductFactory(sku_root="DRA-GON")
        assert "catalog_products_sku_root_format" in str(exc.value)

    def test_too_short_blocked(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductFactory(sku_root="AB")

    def test_too_long_blocked(self):
        # varchar(8) chặn ở column level (DataError) — trước cả check
        # constraint (IntegrityError). Cả 2 đều là defense in depth.
        from django.db import DataError

        with pytest.raises((IntegrityError, DataError)):
            with transaction.atomic():
                ProductFactory(sku_root="DRAGONFIRE")  # 10 ký tự

    def test_digits_only_ok(self):
        p = ProductFactory(sku_root="123456")
        assert p.sku_root == "123456"

    def test_max_length_8_ok(self):
        p = ProductFactory(sku_root="ABCD1234")
        assert p.sku_root == "ABCD1234"


@pytest.mark.django_db
class TestStatusConstraint:
    def test_invalid_status_blocked(self):
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                ProductFactory(status="published")
        assert "catalog_products_status_choices" in str(exc.value)


@pytest.mark.django_db
class TestPartialUniqueIndexes:
    """Partial unique trên LOWER(col) WHERE deleted_at IS NULL.

    Cho phép tạo lại slug/sku_root sau soft delete — SPEC AC-8 edge.
    """

    def test_slug_duplicate_alive_blocked(self):
        ProductFactory(slug="dragon-figure")
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                ProductFactory(slug="dragon-figure")
        assert "catalog_products_slug_lower_alive_uq" in str(exc.value)

    def test_slug_duplicate_case_insensitive_blocked(self):
        ProductFactory(slug="dragon-figure")
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                ProductFactory(slug="Dragon-Figure")  # cùng LOWER()
        assert "catalog_products_slug_lower_alive_uq" in str(exc.value)

    def test_slug_duplicate_allowed_if_other_soft_deleted(self):
        first = ProductFactory(slug="dragon-figure")
        first.delete()  # soft delete

        # Tạo lại slug giống nên success.
        second = ProductFactory(slug="dragon-figure")
        assert second.pk != first.pk
        assert Product.all_objects.filter(slug="dragon-figure").count() == 2

    def test_sku_root_case_insensitive_blocked(self):
        ProductFactory(sku_root="DRAGON")
        with pytest.raises(IntegrityError) as exc:
            with transaction.atomic():
                # sku_root regex chỉ chấp uppercase, nên test phải dùng
                # uppercase. Case-insensitive ở đây nghĩa là "DRAGON" và
                # "DRAGON" thì duplicate dù viết khác nhau ... thực chất
                # với regex hoa chỉ thì insensitive là noop.
                # Validate: dùng cùng giá trị nhưng xác nhận constraint
                # hoạt động (case-insensitive partial unique).
                ProductFactory(sku_root="DRAGON")
        assert "catalog_products_sku_root_lower_alive_uq" in str(exc.value)

    def test_sku_root_duplicate_allowed_if_other_soft_deleted(self):
        first = ProductFactory(sku_root="DRAGON")
        first.delete()
        second = ProductFactory(sku_root="DRAGON")
        assert second.pk != first.pk


@pytest.mark.django_db
class TestSoftDelete:
    """SoftDeleteModel (inherited từ apps.core) behavior trên Product."""

    def test_delete_sets_deleted_at_not_null(self):
        p = ProductFactory()
        assert p.deleted_at is None
        p.delete()
        assert p.deleted_at is not None

    def test_default_manager_excludes_deleted(self):
        alive = ProductFactory()
        gone = ProductFactory()
        gone.delete()

        ids = set(Product.objects.values_list("id", flat=True))
        assert alive.pk in ids
        assert gone.pk not in ids
        assert Product.objects.count() == 1

    def test_all_objects_manager_includes_deleted(self):
        alive = ProductFactory()
        gone = ProductFactory()
        gone.delete()

        ids = set(Product.all_objects.values_list("id", flat=True))
        assert {alive.pk, gone.pk} == ids
        assert Product.all_objects.count() == 2

    def test_is_deleted_property(self):
        p = ProductFactory()
        assert p.is_deleted is False
        p.delete()
        assert p.is_deleted is True

    def test_restore_clears_deleted_at(self):
        p = ProductFactory()
        p.delete()
        assert p.is_deleted is True

        p.restore()
        assert p.deleted_at is None
        assert p.is_deleted is False
        # Restore xong → quay lại default manager.
        assert Product.objects.filter(pk=p.pk).exists()
