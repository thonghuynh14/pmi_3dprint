"""Auth views: login / refresh / logout / me.

Cookie strategy:
- ``access_token`` httpOnly cookie, Path=/, TTL = JWT_ACCESS_TOKEN_LIFETIME
- ``refresh_token`` httpOnly cookie, Path=/api/v1/auth, TTL = JWT_REFRESH_TOKEN_LIFETIME
- ``csrftoken`` non-httpOnly cookie (FE đọc → gửi header X-CSRFToken)

Dev: Secure=False (HTTP localhost). Prod: Secure=True qua env.
"""

from typing import Any

from django.conf import settings
from django.middleware.csrf import get_token as get_csrf_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import ACCESS_COOKIE_NAME
from apps.accounts.serializers.auth import (
    LoginInputSerializer,
    MeOutputSerializer,
    UserOutputSerializer,
)
from apps.accounts.services.auth import (
    auth_login,
    auth_logout,
    auth_refresh,
    get_me_payload,
)


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _cookie_security_flags() -> dict[str, Any]:
    """Default flags cho httpOnly cookies. Secure=True nếu DEBUG=False."""
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
    }


def _set_access_cookie(response: Response, access_jwt: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_jwt,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        **_cookie_security_flags(),
    )


def _set_refresh_cookie(response: Response, refresh_jwt: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_jwt,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=REFRESH_COOKIE_PATH,
        **_cookie_security_flags(),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


class LoginView(APIView):
    """POST /api/v1/auth/login/

    Body: ``{username, password}``. Set 2 httpOnly cookies + csrftoken.
    """

    authentication_classes = ()  # endpoint công khai
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, access_jwt, refresh_jwt = auth_login(**serializer.validated_data)
        # Đảm bảo CSRF cookie được set cho future mutation requests
        get_csrf_token(request)

        response = Response(
            {"user": UserOutputSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        _set_access_cookie(response, access_jwt)
        _set_refresh_cookie(response, refresh_jwt)
        return response


class RefreshView(APIView):
    """POST /api/v1/auth/refresh/

    Đọc refresh_token từ cookie, set lại access_token + refresh_token mới
    (rotation BẬT trong SIMPLE_JWT settings).
    """

    authentication_classes = ()  # public — phụ thuộc cookie
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_jwt = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_jwt:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        new_access, new_refresh = auth_refresh(refresh_token_str=refresh_jwt)

        response = Response(status=status.HTTP_200_OK)
        _set_access_cookie(response, new_access)
        if new_refresh:
            _set_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    """POST /api/v1/auth/logout/

    Blacklist refresh + delete cookies. Idempotent (gọi 2 lần không lỗi).
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_jwt = request.COOKIES.get(REFRESH_COOKIE_NAME)
        auth_logout(refresh_token_str=refresh_jwt)
        response = Response(status=status.HTTP_200_OK)
        _clear_auth_cookies(response)
        return response


class MeView(APIView):
    """GET /api/v1/auth/me/

    Trả profile + permissions cho FE bootstrap UI. Yêu cầu authenticated.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        payload = get_me_payload(
            user=request.user,
            claims=getattr(request, "_jwt_claims", {}) or {},
        )
        return Response(MeOutputSerializer(payload).data)
