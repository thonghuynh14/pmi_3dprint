"""ViewSet cho Variant + APIView cho matrix bulk endpoint.

Thin views — delegate logic xuống service/selector. View chỉ parse
request, dispatch và serialize output.

Permission: hiện chỉ ``IsAuthenticated``. Khi feature ``accounts/RBAC``
ready, replace với role-based permission (xem TODO).
"""

from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.skus.filters import VariantFilter
from apps.skus.models import Variant
from apps.skus.selectors.variants import get_variant, list_variants
from apps.skus.serializers.variants import (
    VariantInputSerializer,
    VariantListItemSerializer,
    VariantMatrixInputSerializer,
    VariantOutputSerializer,
    VariantUpdateSerializer,
)
from apps.skus.services.variants import (
    variant_bulk_create_matrix,
    variant_create,
    variant_restore,
    variant_soft_delete,
    variant_update,
)


class VariantViewSet(viewsets.GenericViewSet):
    """CRUD + restore cho Variant. Lookup qua selector, action qua service."""

    # TODO(accounts): role-based permission
    # (CatalogManager + Designer + SuperAdmin = write; mọi authenticated = read)
    permission_classes = (IsAuthenticated,)

    # PUT tắt — full-replace nguy hiểm với SKU/axis immutable.
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    filter_backends = (DjangoFilterBackend,)
    filterset_class = VariantFilter

    # GenericViewSet lookup qua selector; placeholder cho filter backend
    # + drf-spectacular schema gen.
    queryset = Variant.objects.none()

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
        qs = list_variants(
            product_id=request.query_params.get("product") or None,
            search=request.query_params.get("search", ""),
            status=request.query_params.get("status") or None,
            show_archived=self._is_show_archived(request),
            ordering=request.query_params.get("ordering", "sequence_no"),
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = VariantListItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = VariantListItemSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        variant = get_variant(
            variant_id=pk,
            include_deleted=self._is_show_archived(request),
        )
        return Response(VariantOutputSerializer(variant).data)

    def create(self, request):
        serializer = VariantInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = variant_create(actor=request.user, **serializer.validated_data)
        return Response(
            VariantOutputSerializer(variant).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        variant = get_variant(variant_id=pk)
        serializer = VariantUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = variant_update(
            actor=request.user,
            variant=variant,
            **serializer.validated_data,
        )
        return Response(VariantOutputSerializer(updated).data)

    def destroy(self, request, pk=None):
        variant = get_variant(variant_id=pk)
        variant_soft_delete(actor=request.user, variant=variant)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("post",))
    def restore(self, request, pk=None):
        variant = get_variant(variant_id=pk, include_deleted=True)
        restored = variant_restore(actor=request.user, variant=variant)
        return Response(VariantOutputSerializer(restored).data)


class ProductVariantMatrixView(APIView):
    """``POST /api/v1/catalog/products/<product_id>/variants/bulk-matrix/``.

    Endpoint nested để có ngữ cảnh Product trong URL. Body theo
    ``VariantMatrixInputSerializer``. Trả về ``{count, created: [...]}``.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, product_id):
        serializer = VariantMatrixInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variants = variant_bulk_create_matrix(
            actor=request.user,
            product_id=product_id,
            **serializer.validated_data,
        )
        return Response(
            {
                "count": len(variants),
                "created": VariantOutputSerializer(variants, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )
