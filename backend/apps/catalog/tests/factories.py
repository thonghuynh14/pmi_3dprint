"""Factories cho catalog app.

ProductFactory dùng cho cả model test và service/viewset test (Task 1.3+).
Sequence-based sku_root để chắc chắn unique. Lowercase trong slug, uppercase
trong sku_root khớp CHECK constraint regex.

Lưu ý: accounts app chưa có nên User dùng `django.contrib.auth.User`.
Khi accounts app ready, replace UserFactory ở đây.
"""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from apps.catalog.models import Product

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Sinh user generic cho tests. Catalog Manager role sẽ được áp khi
    có RBAC; lần này chỉ dùng `is_authenticated` để pass permission."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.local")
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker("catch_phrase", locale="en_US")
    slug = factory.Sequence(lambda n: f"product-{n}")
    # 6 ký tự hoa + số, không đụng nhau (PRD + 4 chữ số 0-padded).
    sku_root = factory.Sequence(lambda n: f"PRD{n:04d}")
    status = Product.Status.DRAFT
    short_description = factory.Faker("sentence", nb_words=8)
    long_description = ""
    brand = ""
    tags = factory.LazyFunction(list)
    attributes = factory.LazyFunction(dict)
