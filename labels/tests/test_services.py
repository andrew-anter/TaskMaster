import pytest
from labels.services import LabelService
from labels.models import Label

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
        label = service.create_label_for_task(name="Task Label", color="#654321", task=task)
        
        assert label.name == "Task Label"
        assert task.labels.filter(id=label.id).exists()
        assert label.owner == user

    def test_update_label(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="Old Name", color="#000000")
        
        updated_label = service.update_label(pk=label.pk, name="New Name", color="#FFFFFF")
        
        assert updated_label.name == "New Name"
        assert updated_label.color == "#FFFFFF"

    def test_delete_label(self, user):
        service = LabelService(user=user)
        label = service.create_label(name="To Delete", color="#000000")
        
        service.delete_label(pk=label.pk)
        
        assert not Label.objects.filter(pk=label.pk).exists()
