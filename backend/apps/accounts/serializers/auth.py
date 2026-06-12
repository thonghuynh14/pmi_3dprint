"""Serializer cho auth endpoints (login + user output)."""

from rest_framework import serializers

from apps.accounts.models import User


class LoginInputSerializer(serializers.Serializer):
    """Body của POST /auth/login/."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class UserOutputSerializer(serializers.ModelSerializer):
    """Output trả về sau login + qua /auth/me/."""

    role = serializers.CharField(source="role.code", default=None, read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "full_name", "role", "is_active")
        read_only_fields = fields


class MeOutputSerializer(serializers.Serializer):
    """Output của /auth/me/: user + permissions (cho FE bootstrap UI)."""

    user = UserOutputSerializer()
    permissions = serializers.ListField(child=serializers.CharField())
