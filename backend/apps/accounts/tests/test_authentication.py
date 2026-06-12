"""Tests cho CookieJWTAuthentication.

Test trực tiếp class authenticate(), không qua URL — isolated unit test.
Integration test login + cookie ở test_api_auth.py.
"""

from __future__ import annotations

import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.accounts.authentication import ACCESS_COOKIE_NAME, CookieJWTAuthentication
from apps.accounts.jwt_utils import CustomRefreshToken
from apps.accounts.tests.factories import make_user


@pytest.fixture
def factory():
    return APIRequestFactory()


@pytest.fixture
def auth():
    return CookieJWTAuthentication()


@pytest.mark.django_db
class TestCookieJWTAuthentication:
    def test_returns_none_when_no_cookie(self, auth, factory):
        request = factory.get("/")
        # APIRequestFactory không tạo wrapper DRF Request; làm thủ công.
        from rest_framework.request import Request

        result = auth.authenticate(Request(request))
        assert result is None

    def test_authenticates_with_valid_cookie(self, auth, factory):
        from rest_framework.request import Request

        user = make_user("super_admin")
        access = str(CustomRefreshToken.for_user(user).access_token)

        request = factory.get("/")
        request.COOKIES = {ACCESS_COOKIE_NAME: access}
        drf_request = Request(request)

        auth_user, token = auth.authenticate(drf_request)
        assert auth_user.id == user.id
        assert drf_request._jwt_claims["role"] == "super_admin"
        assert "user:manage" in drf_request._jwt_claims["permissions"]

    def test_rejects_invalid_token(self, auth, factory):
        from rest_framework.request import Request

        request = factory.get("/")
        request.COOKIES = {ACCESS_COOKIE_NAME: "garbage"}
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(Request(request))

    def test_rejects_deactivated_user(self, auth, factory):
        from rest_framework.request import Request

        user = make_user("cashier")
        access = str(CustomRefreshToken.for_user(user).access_token)
        user.is_active = False
        user.save()

        request = factory.get("/")
        request.COOKIES = {ACCESS_COOKIE_NAME: access}
        # simplejwt's get_user() raise AuthenticationFailed("User is inactive")
        # trước khi đụng đến custom check trong CookieJWTAuthentication.
        # Cả 2 path đều cho 401 → đủ cho AC.
        with pytest.raises(AuthenticationFailed) as exc_info:
            auth.authenticate(Request(request))
        assert "inactive" in str(exc_info.value).lower() or "vô hiệu" in str(
            exc_info.value
        )
