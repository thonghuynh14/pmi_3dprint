"""Custom JWT token với role + permissions claim.

Subclass `rest_framework_simplejwt.RefreshToken` để inject extra claims
khi tạo token (login + refresh). Permission class sau này đọc từ
``request._jwt_claims['permissions']`` thay vì DB lookup → O(1).

Trade-off: đổi role không phản ánh ngay; phải đợi access token expire
(max 15 phút). Đã ghi trong BR-012.
"""

from typing import TYPE_CHECKING

from rest_framework_simplejwt.tokens import RefreshToken

if TYPE_CHECKING:
    from apps.accounts.models import User


class CustomRefreshToken(RefreshToken):
    """Refresh token mang role + permissions trong cả access lẫn refresh
    payload. Khi rotate, access mới được gen từ refresh nên cũng giữ claim.
    """

    @classmethod
    def for_user(cls, user: "User") -> "CustomRefreshToken":  # type: ignore[override]
        token = super().for_user(user)
        # Inject extra claim vào token (cả access và refresh).
        token["username"] = user.username
        token["role"] = user.role.code if user.role_id else None
        # `permission_codes` property KHÔNG cache, gọi DB 1 lần — chấp nhận
        # vì login + refresh ít hơn nhiều so với mỗi request authenticated.
        token["permissions"] = user.permission_codes
        return token
