"""Root URL config. Mọi API mount dưới /api/v1/."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Auth endpoints — JWT (simplejwt). Tạm thay cho feature `accounts/auth UI`
# (defer per ANALYSIS OQ-2). Catalog Manager dùng để lấy token test API.
auth_patterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

api_v1_patterns = [
    path("auth/", include((auth_patterns, "auth"))),
    path("catalog/", include("apps.catalog.urls")),
    # Sẽ include thêm khi triển khai feature:
    # path("skus/", include("apps.skus.urls")),
    # ...
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("api/v1/", include((api_v1_patterns, "v1"))),
    # OpenAPI schema + docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
