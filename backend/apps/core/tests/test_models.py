"""Smoke tests cho base models. Chỉ kiểm tra abstract structure, chưa migrate."""

import pytest

from apps.core.models import AuditLog, BaseModel, SoftDeleteModel, TimestampedModel


def test_abstract_models_are_abstract():
    assert TimestampedModel._meta.abstract is True
    assert SoftDeleteModel._meta.abstract is True
    assert BaseModel._meta.abstract is True


def test_audit_log_choices_include_business_events():
    actions = {choice[0] for choice in AuditLog.Action.choices}
    assert "create" in actions
    assert "license_changed" in actions
    assert "channel.published" in actions


@pytest.mark.django_db
def test_audit_log_can_be_created(django_user_model):
    user = django_user_model.objects.create(username="alice")
    from django.contrib.contenttypes.models import ContentType

    log = AuditLog.objects.create(
        entity_type=ContentType.objects.get_for_model(user),
        entity_id=str(user.pk),
        action=AuditLog.Action.CREATE,
        actor=user,
        changes={"username": [None, "alice"]},
    )
    assert log.pk is not None
    assert log.action == "create"
