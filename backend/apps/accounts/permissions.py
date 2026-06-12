"""DRF permission classes dựa trên JWT claims.

Thiết kế:
- ``HasPermission(perm_code)``: factory-style — instantiate với code chuỗi.
- ``ActionPermission``: ViewSet-friendly — map action name → perm code.

Đọc permission từ ``request._jwt_claims`` (gắn bởi
`CookieJWTAuthentication`). Nếu authenticator không phải Cookie variant
(vd test với force_authenticate) thì fallback sang
``request.user.permission_codes`` (DB lookup 1 lần).

Trả về 403 khi không có quyền (DRF default).
"""

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.views import APIView
    from rest_framework.request import Request


def _claims_permissions(request: "Request") -> set[str]:
    """Lấy set permission code của user hiện tại.

    Ưu tiên JWT claims (đã decode khi authenticate). Fallback DB lookup
    cho test/force_authenticate.
    """
    claims = getattr(request, "_jwt_claims", None)
    if claims is not None:
        return set(claims.get("permissions") or [])

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return set()
    return set(user.permission_codes)


def _is_superuser_shortcircuit(request: "Request") -> bool:
    """Django convention: is_superuser bypass mọi permission check.

    Áp dụng cho:
    - JWT claim role == 'super_admin'
    - User.is_superuser=True (kể cả khi role chưa gán, vd test fixture
      hoặc Django shell tạo nhanh user qua createsuperuser).
    """
    claims = getattr(request, "_jwt_claims", None)
    if claims is not None and claims.get("role") == "super_admin":
        return True
    user = getattr(request, "user", None)
    return bool(user and getattr(user, "is_superuser", False))


class HasPermission(BasePermission):
    """Permission class kiểm tra 1 code cụ thể.

    Dùng trong ``permission_classes`` của view đơn lẻ:

        class MyView(APIView):
            permission_classes = [HasPermission.with_code('product:create')]
    """

    required_code: str = ""  # subclass override

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if _is_superuser_shortcircuit(request):
            return True
        return self.required_code in _claims_permissions(request)

    @classmethod
    def with_code(cls, code: str) -> type["HasPermission"]:
        """Tạo subclass động cho 1 code (DRF cần class chứ không phải instance)."""
        return type(
            f"HasPermission_{code.replace(':', '_')}",
            (cls,),
            {"required_code": code},
        )


class ActionPermission(BasePermission):
    """Permission class map ``view.action`` → permission code.

    ViewSet định nghĩa ``action_permission_map`` class attribute:

        class ProductViewSet(viewsets.GenericViewSet):
            permission_classes = [ActionPermission]
            action_permission_map = {
                'list': 'product:read',
                'create': 'product:create',
                ...
            }

    Action không có trong map → fallback ``view.default_permission`` nếu
    có, không thì 403.
    """

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if _is_superuser_shortcircuit(request):
            return True

        perm_map: dict[str, str] = getattr(view, "action_permission_map", {})
        action = getattr(view, "action", None)

        required = perm_map.get(action) if action else None
        if required is None:
            required = getattr(view, "default_permission", None)
        if required is None:
            return False

        return required in _claims_permissions(request)
