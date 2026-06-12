"""URLs cho accounts app.

Mount tại /api/v1/auth/ trong config.urls.
"""

from django.urls import path

from apps.accounts.views.auth import LoginView, LogoutView, MeView, RefreshView


app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
