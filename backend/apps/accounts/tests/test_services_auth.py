"""Tests cho auth services (login/refresh/logout)."""

from __future__ import annotations

import pytest

from apps.accounts.exceptions import InvalidCredentialsError
from apps.accounts.jwt_utils import CustomRefreshToken
from apps.accounts.services.auth import (
    auth_login,
    auth_logout,
    auth_refresh,
    get_me_payload,
)
from apps.accounts.tests.factories import UserFactory, make_user


@pytest.mark.django_db
class TestAuthLogin:
    def test_returns_tokens_for_valid_credentials(self):
        user = UserFactory(username="alice", password="secretpw")
        u, access, refresh = auth_login(username="alice", password="secretpw")
        assert u.id == user.id
        assert isinstance(access, str) and len(access) > 50
        assert isinstance(refresh, str) and len(refresh) > 50

    def test_raises_for_wrong_password(self):
        UserFactory(username="bob", password="rightpw")
        with pytest.raises(InvalidCredentialsError):
            auth_login(username="bob", password="wrong")

    def test_raises_for_nonexistent_user(self):
        with pytest.raises(InvalidCredentialsError):
            auth_login(username="ghost", password="x")

    def test_raises_for_inactive_user(self):
        UserFactory(username="frozen", password="pw", is_active=False)
        with pytest.raises(InvalidCredentialsError):
            auth_login(username="frozen", password="pw")


@pytest.mark.django_db
class TestAuthRefresh:
    def test_returns_new_access_token(self):
        user = make_user("super_admin", password="pw")
        _, _, refresh = auth_login(username=user.username, password="pw")
        new_access, new_refresh = auth_refresh(refresh_token_str=refresh)
        assert isinstance(new_access, str) and len(new_access) > 50
        # Rotation BẬT → có refresh mới
        assert new_refresh is not None and new_refresh != refresh

    def test_raises_for_invalid_refresh(self):
        with pytest.raises(InvalidCredentialsError):
            auth_refresh(refresh_token_str="not-a-real-jwt")

    def test_raises_when_user_deactivated_after_login(self):
        user = make_user("cashier", password="pw")
        _, _, refresh = auth_login(username=user.username, password="pw")
        user.is_active = False
        user.save()
        with pytest.raises(InvalidCredentialsError):
            auth_refresh(refresh_token_str=refresh)

    def test_old_refresh_blacklisted_after_rotation(self):
        user = make_user("super_admin", password="pw")
        _, _, refresh = auth_login(username=user.username, password="pw")
        auth_refresh(refresh_token_str=refresh)  # consume + rotate
        # Refresh cũ phải bị reject (đã blacklist)
        with pytest.raises(InvalidCredentialsError):
            auth_refresh(refresh_token_str=refresh)


@pytest.mark.django_db
class TestAuthLogout:
    def test_blacklists_refresh_token(self):
        user = make_user("super_admin", password="pw")
        _, _, refresh = auth_login(username=user.username, password="pw")
        auth_logout(refresh_token_str=refresh)
        with pytest.raises(InvalidCredentialsError):
            auth_refresh(refresh_token_str=refresh)

    def test_idempotent_with_none(self):
        # Không raise
        auth_logout(refresh_token_str=None)

    def test_idempotent_with_invalid_token(self):
        # Không raise dù token rác
        auth_logout(refresh_token_str="garbage")


@pytest.mark.django_db
class TestMePayload:
    def test_prefers_claims_permissions(self):
        user = make_user("catalog_manager")
        payload = get_me_payload(
            user=user, claims={"permissions": ["custom:override"]}
        )
        assert payload["permissions"] == ["custom:override"]

    def test_fallback_db_when_no_claims(self):
        user = make_user("catalog_manager")
        payload = get_me_payload(user=user, claims={})
        assert "product:create" in payload["permissions"]
