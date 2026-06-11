"""URL routes cho skus app.

Mount dưới ``/api/v1/skus/`` (xem config/urls.py).

Matrix endpoint nested dưới ``/catalog/products/<id>/variants/bulk-matrix/``
mount riêng ở config/urls.py để giữ ngữ cảnh Product trong URL.
"""

from rest_framework.routers import DefaultRouter

from apps.skus.views.variants import VariantViewSet

router = DefaultRouter()
router.register(r"variants", VariantViewSet, basename="variant")

urlpatterns = router.urls
