"""django-filter FilterSet cho Variant list endpoint."""

from __future__ import annotations

from django.db.models import Q
from django_filters import rest_framework as filters

from apps.skus.models import Variant


class VariantFilter(filters.FilterSet):
    """Filters bind vào query params của ``GET /skus/variants/``.

    - ``search``: icontains trên ``sku`` HOẶC ``name`` (GIN trgm index).
    - ``status``: exact match.
    - ``product``: UUID filter theo product (parent).
    - ``show_archived``: chuyển sang selector — không apply ở filterset
      (kế thừa cách Product làm).
    """

    search = filters.CharFilter(method="filter_search")
    status = filters.ChoiceFilter(choices=Variant.Status.choices)
    product = filters.UUIDFilter(field_name="product_id")

    class Meta:
        model = Variant
        fields = ("search", "status", "product")

    def filter_search(self, queryset, name, value):  # noqa: ARG002
        if not value:
            return queryset
        return queryset.filter(Q(sku__icontains=value) | Q(name__icontains=value))
