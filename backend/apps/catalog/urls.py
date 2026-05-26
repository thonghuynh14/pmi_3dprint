"""URL routes cho catalog app.

Mount dưới /api/v1/catalog/ (xem config/urls.py).
"""

from rest_framework.routers import DefaultRouter

from apps.catalog.views.products import ProductViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")

urlpatterns = router.urls
