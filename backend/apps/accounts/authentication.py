"""Cookie-based JWT authentication.

Đọc ``access_token`` từ HTTP cookie thay vì ``Authorization: Bearer ...``
header. Cho phép FE giữ token httpOnly (đỡ XSS) — xem
docs/features/03-accounts-rbac/SPEC.md.

Gắn payload đã decode vào ``request._jwt_claims`` để permission class
đọc danh sách permission O(1) — không touch DB.

Authentication failure khi:
- Cookie không có → trả None (DRF tiếp tục thử authenticator khác)
- Cookie có nhưng token invalid → raise AuthenticationFailed
- User ``is_active=False`` → raise AuthenticationFailed (kể cả token hợp lệ)
"""

from typing import TYPE_CHECKING

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

if TYPE_CHECKING:
    from rest_framework.request import Request


ACCESS_COOKIE_NAME = "access_token"


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticator đọc JWT từ cookie. Fallback (None) thay vì raise
    nếu cookie không tồn tại — cho phép endpoint public (login, csrf) đi qua.
    """

    def authenticate(self, request: "Request"):  # type: ignore[override]
        raw_token = request.COOKIES.get(ACCESS_COOKIE_NAME)
        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError) as exc:
            # Cookie có nhưng token hỏng → 401, KHÔNG fallback sang
            # authenticator khác (tránh ambiguous error).
            raise AuthenticationFailed(
                detail="Token không hợp lệ hoặc đã hết hạn.",
                code="invalid_token",
            ) from exc

        user = self.get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed(
                detail="Tài khoản đã bị vô hiệu hoá.",
                code="user_inactive",
            )

        # Gắn payload vào request cho permission class.
        # JWTAuthentication.get_validated_token trả về dict-like; payload
        # là attribute (simplejwt Token).
        request._jwt_claims = dict(validated_token.payload)  # type: ignore[attr-defined]
        return (user, validated_token)
