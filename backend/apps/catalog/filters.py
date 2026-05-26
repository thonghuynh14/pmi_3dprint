"""django-filter FilterSet cho Product list endpoint."""

from __future__ import annotations

from django.db.models import Q
from django_filters import rest_framework as filters

from apps.catalog.models import Product


class ProductFilter(filters.FilterSet):
    """Filters bind vào query params của GET /products/.

    `search`: ?search=dragon → match icontains trên name HOẶC sku_root.
        GIN trgm index (migration 0001) tăng tốc.
    `status`: ?status=active → exact match.
    `show_archived`: ?show_archived=true → kế thừa logic ở selector
        (filter này không apply, view chuyển show_archived sang selector).
    """

    search = filters.CharFilter(method="filter_search")
    status = filters.ChoiceFilter(choices=Product.Status.choices)

    class Meta:
        model = Product
        fields = ("search", "status")

    def filter_search(self, queryset, name, value):  # noqa: ARG002
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(sku_root__icontains=value)
        )
