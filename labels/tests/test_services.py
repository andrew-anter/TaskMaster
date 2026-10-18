import pytest

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

    def test_create_label_for_task(self, user, task):
        service = LabelService(user=user)
        label = service.create_label_for_task(
            name="Task Label", color="#654321", task=task
        )

        assert label.name == "Task Label"
        assert task.labels.filter(id=label.pk).exists()
        assert label.owner == user

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
