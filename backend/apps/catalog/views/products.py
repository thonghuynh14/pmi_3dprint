"""ViewSet cho Product.

Thin viewset — delegate logic xuống service/selector. ViewSet chỉ parse
request, dispatch và serialize output.

Permission: ``ActionPermission`` map action → permission code từ JWT
claims (xem feature 03-accounts-rbac).
"""

from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ActionPermission
from apps.catalog.filters import ProductFilter
from apps.catalog.selectors.products import get_product, list_products
from apps.catalog.serializers.products import (
    ProductInputSerializer,
    ProductListItemSerializer,
    ProductOutputSerializer,
)
from apps.catalog.services.products import (
    product_create,
    product_restore,
    product_soft_delete,
    product_update,
)


class ProductViewSet(viewsets.GenericViewSet):
    permission_classes = (ActionPermission,)
    action_permission_map = {
        "list": "product:read",
        "retrieve": "product:read",
        "create": "product:create",
        "partial_update": "product:update",
        "destroy": "product:delete",
        "restore": "product:update",
    }

    # PUT tắt — chỉ PATCH (xem DESIGN Decision 4)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter

    # GenericViewSet không tự lấy queryset; ta lookup qua selector.
    # Set placeholder để DjangoFilterBackend không bị None.
    queryset = ProductListItemSerializer.Meta.model.objects.none()

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _is_show_archived(self, request) -> bool:
        value = request.query_params.get("show_archived", "").lower()
        return value in ("true", "1", "yes")

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------

    def list(self, request):
        qs = list_products(
            search=request.query_params.get("search", ""),
            status=request.query_params.get("status") or None,
            show_archived=self._is_show_archived(request),
            ordering=request.query_params.get("ordering", "-updated_at"),
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductListItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductListItemSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        product = get_product(
            product_id=pk,
            include_deleted=self._is_show_archived(request),
        )
        return Response(ProductOutputSerializer(product).data)

    def create(self, request):
        serializer = ProductInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = product_create(actor=request.user, **serializer.validated_data)
        return Response(
            ProductOutputSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        product = get_product(product_id=pk)
        serializer = ProductInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = product_update(
            actor=request.user,
            product=product,
            **serializer.validated_data,
        )
        return Response(ProductOutputSerializer(updated).data)

    def destroy(self, request, pk=None):
        product = get_product(product_id=pk)
        product_soft_delete(actor=request.user, product=product)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("post",))
    def restore(self, request, pk=None):
        # Cần include_deleted=True vì product đang ở scope archived.
        product = get_product(product_id=pk, include_deleted=True)
        restored = product_restore(actor=request.user, product=product)
        return Response(ProductOutputSerializer(restored).data)
