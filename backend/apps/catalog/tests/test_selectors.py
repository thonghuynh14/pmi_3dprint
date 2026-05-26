"""Tests cho selectors/products.py."""

from __future__ import annotations

import uuid

import pytest

from apps.catalog.exceptions import ProductNotFoundError
from apps.catalog.models import Product
from apps.catalog.selectors.products import get_product, list_products

from .factories import ProductFactory


# ---------------------------------------------------------------------------
# get_product
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetProduct:
    def test_returns_existing_product(self):
        product = ProductFactory()
        result = get_product(product_id=product.pk)
        assert result.pk == product.pk

    def test_missing_id_raises_not_found(self):
        random_id = uuid.uuid4()
        with pytest.raises(ProductNotFoundError):
            get_product(product_id=random_id)

    def test_invalid_uuid_raises_not_found(self):
        with pytest.raises(ProductNotFoundError):
            get_product(product_id="not-a-uuid")

    def test_soft_deleted_default_raises_not_found(self):
        product = ProductFactory()
        product.delete()  # soft delete
        with pytest.raises(ProductNotFoundError):
            get_product(product_id=product.pk)

    def test_soft_deleted_include_deleted_returns_product(self):
        product = ProductFactory()
        product.delete()
        result = get_product(product_id=product.pk, include_deleted=True)
        assert result.pk == product.pk
        assert result.deleted_at is not None


# ---------------------------------------------------------------------------
# list_products
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListProducts:
    def test_default_excludes_archived(self):
        alive_a = ProductFactory()
        alive_b = ProductFactory()
        archived = ProductFactory()
        archived.delete()

        result = list_products()
        ids = set(result.values_list("id", flat=True))
        assert ids == {alive_a.pk, alive_b.pk}

    def test_show_archived_includes_deleted(self):
        alive = ProductFactory()
        archived = ProductFactory()
        archived.delete()

        result = list_products(show_archived=True)
        ids = set(result.values_list("id", flat=True))
        assert ids == {alive.pk, archived.pk}

    def test_search_matches_name_icontains(self):
        target = ProductFactory(name="Dragon Figure")
        ProductFactory(name="Phone Case")
        ProductFactory(name="Vase")

        result = list_products(search="dragon")
        assert list(result.values_list("id", flat=True)) == [target.pk]

    def test_search_matches_name_case_insensitive(self):
        target = ProductFactory(name="Dragon Figure")
        ProductFactory(name="Phone Case")
        result = list_products(search="DRAGON")
        assert list(result.values_list("id", flat=True)) == [target.pk]

    def test_search_matches_sku_root_icontains(self):
        target = ProductFactory(sku_root="DRAGON")
        ProductFactory(sku_root="PHCASE")

        result = list_products(search="dragon")
        ids = list(result.values_list("id", flat=True))
        assert target.pk in ids

    def test_search_matches_either_name_or_sku_root(self):
        by_name = ProductFactory(name="Foo Dragon", sku_root="ABC")
        by_sku = ProductFactory(name="Bar", sku_root="DRAGON")
        ProductFactory(name="X", sku_root="YYY")

        result = list_products(search="dragon")
        ids = set(result.values_list("id", flat=True))
        assert ids == {by_name.pk, by_sku.pk}

    def test_filter_status(self):
        draft = ProductFactory(status=Product.Status.DRAFT)
        active = ProductFactory(status=Product.Status.ACTIVE)

        result = list_products(status=Product.Status.ACTIVE)
        assert list(result.values_list("id", flat=True)) == [active.pk]
        assert draft.pk not in result.values_list("id", flat=True)

    def test_filter_status_none_returns_all(self):
        ProductFactory(status=Product.Status.DRAFT)
        ProductFactory(status=Product.Status.ACTIVE)

        result = list_products(status=None)
        assert result.count() == 2

    def test_default_ordering_updated_at_desc(self):
        first = ProductFactory()
        second = ProductFactory()
        # Bump first's updated_at by saving again.
        first.save()

        result = list_products()
        ids = list(result.values_list("id", flat=True))
        assert ids == [first.pk, second.pk]  # first updated later → first

    def test_custom_ordering(self):
        b = ProductFactory(name="Beta")
        a = ProductFactory(name="Alpha")

        result = list_products(ordering="name")
        ids = list(result.values_list("id", flat=True))
        assert ids == [a.pk, b.pk]

    def test_combined_search_status_show_archived(self):
        # Có 1 product match cả search + status + archived
        target = ProductFactory(name="Dragon Archived", status=Product.Status.ARCHIVED)
        target.delete()
        ProductFactory(name="Dragon Alive", status=Product.Status.ARCHIVED)  # alive ≠ deleted
        ProductFactory(name="Other", status=Product.Status.ARCHIVED)

        result = list_products(
            search="dragon",
            status=Product.Status.ARCHIVED,
            show_archived=True,
        )
        ids = set(result.values_list("id", flat=True))
        assert target.pk in ids
