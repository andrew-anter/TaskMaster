import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction

from accounts.models import User
from labels.exceptions import DuplicateLabelError
from labels.models import Label
from labels.services import LabelService


@pytest.mark.django_db
class TestLabelService:
    def test_create_label(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="Test Label", color="#123456")

        assert label.name == "Test Label"
        assert label.color == "#123456"
        assert label.owner == user

    def test_create_label_with_overlong_name_is_rejected(self, user):
        service = LabelService(user=user)

        with pytest.raises(DjangoValidationError):
            service.create_label(name="x" * 51, color="#123456")

        assert not Label.objects.filter(owner=user).exists()

    def test_update_label(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="Old Name", color="#000000")

        updated_label = service.update_label(
            pk=label.pk, name="New Name", color="#FFFFFF"
        )

        assert updated_label.name == "New Name"
        assert updated_label.color == "#FFFFFF"

    def test_delete_label(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="To Delete", color="#000000")

        service.delete_label(pk=label.pk)

        assert not Label.objects.filter(pk=label.pk).exists()

    def test_create_duplicate_name_raises(self, user):
        service = LabelService(user=user)
        service.create_label(name="Duplicated", color="#000000")

        with pytest.raises(DuplicateLabelError):
            service.create_label(name="duplicated", color="#111111")

        assert Label.objects.filter(owner=user).count() == 1

    def test_create_label_translates_integrity_error_to_duplicate(
        self, user, monkeypatch
    ):
        service = LabelService(user=user)
        service.create_label(name="Raced", color="#000000")

        # Simulate losing the pre-check race: skip both the service check and
        # model validation so the INSERT itself hits the unique constraint.
        monkeypatch.setattr(service, "_check_name_is_free", lambda *a, **k: None)
        monkeypatch.setattr(Label, "full_clean", lambda self, *a, **k: None)

        with pytest.raises(DuplicateLabelError):
            service.create_label(name="Raced", color="#111111")

        assert Label.objects.filter(owner=user, name="Raced").count() == 1

    def test_update_label_translates_integrity_error_to_duplicate(
        self, user, monkeypatch
    ):
        service = LabelService(user=user)
        service.create_label(name="Raced", color="#000000")
        label = service.create_label(name="Other", color="#111111")

        monkeypatch.setattr(service, "_check_name_is_free", lambda *a, **k: None)
        monkeypatch.setattr(Label, "full_clean", lambda self, *a, **k: None)

        with pytest.raises(DuplicateLabelError):
            service.update_label(pk=label.pk, name="Raced")

        label.refresh_from_db()
        assert label.name == "Other"

    def test_database_rejects_duplicate_name_for_owner(self, user):
        LabelService(user=user).create_label(name="Unique", color="#000000")

        with pytest.raises(IntegrityError), transaction.atomic():
            Label.objects.create(name="Unique", color="#111111", owner=user)

    def test_another_users_label_name_is_free(self, user):
        other = User.objects.create_user(username="other")
        LabelService(user=other).create_label(name="Shared name", color="#000000")

        label = LabelService(user=user).create_label(
            name="Shared name", color="#111111"
        )

        assert label.pk is not None

    def test_update_to_existing_name_raises(self, user):
        service = LabelService(user=user)
        service.create_label(name="First", color="#000000")
        second = service.create_label(name="Second", color="#111111")

        with pytest.raises(DuplicateLabelError):
            service.update_label(pk=second.pk, name="First")

    def test_update_keeps_own_name(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="Keep me", color="#000000")

        updated = service.update_label(pk=label.pk, name="Keep me", color="#222222")

        assert updated.color == "#222222"
