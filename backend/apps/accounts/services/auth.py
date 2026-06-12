"""Auth service: login / refresh / logout.

Mọi business logic ở đây — views chỉ parse request + set cookie.
"""

from typing import Any

from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.exceptions import InvalidCredentialsError
from apps.accounts.jwt_utils import CustomRefreshToken
from apps.accounts.models import User


def auth_login(*, username: str, password: str) -> tuple[User, str, str]:
    """Xác thực credentials, trả (user, access_jwt, refresh_jwt).

    Raises:
        InvalidCredentialsError: username/password sai hoặc user inactive.

    Note: ``authenticate()`` đã check ``is_active`` (ModelBackend mặc định).
    """
    user = authenticate(username=username, password=password)
    if user is None:
        raise InvalidCredentialsError()

    refresh = CustomRefreshToken.for_user(user)
    return user, str(refresh.access_token), str(refresh)


def auth_refresh(*, refresh_token_str: str) -> tuple[str, str | None]:
    """Refresh access token. Nếu ROTATE_REFRESH_TOKENS bật, trả refresh mới.

    Returns:
        (new_access_jwt, new_refresh_jwt | None)

    Raises:
        InvalidCredentialsError: refresh expired/blacklisted/invalid.
    """
    try:
        # Dùng base RefreshToken để parse, sau đó cycle để rotate + blacklist.
        refresh = RefreshToken(refresh_token_str)
    except (TokenError, InvalidToken) as exc:
        raise InvalidCredentialsError(detail="Refresh token không hợp lệ.") from exc

    # Lấy user từ claim user_id để re-encode role + permissions (case user
    # đã đổi role giữa các refresh).
    user_id = refresh.payload.get("user_id")
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist as exc:
        raise InvalidCredentialsError(detail="User không tồn tại hoặc inactive.") from exc

    # Tạo refresh mới với claim updated. simplejwt sẽ blacklist refresh cũ
    # (BLACKLIST_AFTER_ROTATION=True ở settings).
    new_refresh = CustomRefreshToken.for_user(user)
    # Blacklist refresh cũ thủ công (vì ta không gọi qua TokenRefreshView)
    try:
        refresh.blacklist()
    except AttributeError:
        # Trường hợp token_blacklist không enable — skip.
        pass

    return str(new_refresh.access_token), str(new_refresh)


def auth_logout(*, refresh_token_str: str | None) -> None:
    """Blacklist refresh token. Idempotent: token đã blacklist → bỏ qua.

    Nếu refresh_token_str=None (cookie expired/missing), coi như logout
    succeed — view sẽ vẫn xoá cookie.
    """
    if not refresh_token_str:
        return
    try:
        RefreshToken(refresh_token_str).blacklist()
    except (TokenError, InvalidToken, AttributeError):
        # Token đã invalid / blacklist app chưa enable → silent
        pass


def get_me_payload(*, user: User, claims: dict[str, Any]) -> dict[str, Any]:
    """Build payload cho /auth/me/.

    Ưu tiên claims (đã có sẵn permissions). Nếu không có claims (test
    với force_authenticate), fallback DB lookup.
    """
    permissions = claims.get("permissions") if claims else None
    if permissions is None:
        permissions = user.permission_codes
    return {
        "user": user,
        "permissions": permissions,
    }
