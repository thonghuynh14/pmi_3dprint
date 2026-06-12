"""Integration tests cho 4 auth endpoint via APIClient."""

from __future__ import annotations

import pytest

from apps.accounts.authentication import ACCESS_COOKIE_NAME
from apps.accounts.tests.factories import UserFactory, make_user
from apps.accounts.views.auth import REFRESH_COOKIE_NAME


LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
REFRESH_URL = "/api/v1/auth/refresh/"
ME_URL = "/api/v1/auth/me/"


@pytest.mark.django_db
class TestLoginEndpoint:
    def test_returns_200_and_sets_cookies(self, api_client):
        UserFactory(username="alice", password="pw")
        response = api_client.post(
            LOGIN_URL,
            data={"username": "alice", "password": "pw"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["user"]["username"] == "alice"
        # Cookies
        assert ACCESS_COOKIE_NAME in response.cookies
        assert REFRESH_COOKIE_NAME in response.cookies
        assert response.cookies[ACCESS_COOKIE_NAME]["httponly"]
        assert response.cookies[REFRESH_COOKIE_NAME]["path"] == "/api/v1/auth"

    def test_returns_401_for_invalid_creds(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            data={"username": "ghost", "password": "x"},
            format="json",
        )
        assert response.status_code == 401

    def test_400_for_missing_fields(self, api_client):
        response = api_client.post(LOGIN_URL, data={}, format="json")
        assert response.status_code == 400

    def test_includes_role_in_user_payload(self, api_client):
        make_user("super_admin", username="admin", password="pw")
        response = api_client.post(
            LOGIN_URL,
            data={"username": "admin", "password": "pw"},
            format="json",
        )
        assert response.data["user"]["role"] == "super_admin"


@pytest.mark.django_db
class TestMeEndpoint:
    def test_401_without_auth(self, api_client):
        response = api_client.get(ME_URL)
        assert response.status_code == 401

    def test_returns_user_and_permissions(self, api_client):
        make_user("catalog_manager", username="cm", password="pw")
        api_client.post(
            LOGIN_URL, data={"username": "cm", "password": "pw"}, format="json"
        )
        response = api_client.get(ME_URL)
        assert response.status_code == 200
        assert response.data["user"]["username"] == "cm"
        assert "product:create" in response.data["permissions"]
        assert "channel:publish" not in response.data["permissions"]


@pytest.mark.django_db
class TestRefreshEndpoint:
    def test_401_without_refresh_cookie(self, api_client):
        response = api_client.post(REFRESH_URL)
        assert response.status_code == 401

    def test_returns_new_access_cookie(self, api_client):
        make_user("super_admin", username="admin", password="pw")
        api_client.post(
            LOGIN_URL, data={"username": "admin", "password": "pw"}, format="json"
        )
        old_access = api_client.cookies[ACCESS_COOKIE_NAME].value
        response = api_client.post(REFRESH_URL)
        assert response.status_code == 200
        new_access = response.cookies[ACCESS_COOKIE_NAME].value
        assert new_access != old_access


@pytest.mark.django_db
class TestLogoutEndpoint:
    def test_clears_cookies_and_blacklists_refresh(self, api_client):
        make_user("cashier", username="c1", password="pw")
        api_client.post(
            LOGIN_URL, data={"username": "c1", "password": "pw"}, format="json"
        )
        response = api_client.post(LOGOUT_URL)
        assert response.status_code == 200
        # set_cookie với Max-Age=0 → mark expired
        assert response.cookies[ACCESS_COOKIE_NAME]["max-age"] == 0
        assert response.cookies[REFRESH_COOKIE_NAME]["max-age"] == 0

    def test_idempotent_without_cookies(self, api_client):
        """Gọi logout khi chưa login → vẫn 200 (idempotent)."""
        response = api_client.post(LOGOUT_URL)
        assert response.status_code == 200
