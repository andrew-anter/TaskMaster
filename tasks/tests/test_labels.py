import pytest
from tasks.services import task_add_service, task_update_service
from tasks.selectors import get_tasks_by_label
from labels.models import Label

@pytest.mark.django_db
class TestTaskLabels:
    def test_add_task_with_labels(self, owner):
        label1 = Label.objects.create(name="L1", color="#111111", owner=owner)
        label2 = Label.objects.create(name="L2", color="#222222", owner=owner)
        
        task = task_add_service(
            title="Task with labels",
            description="Desc",
            owner=owner,
            labels=[label1.id, label2.id]
        )
        
        assert task.labels.count() == 2
        assert label1 in task.labels.all()
        assert label2 in task.labels.all()

    def test_update_task_labels(self, owner, task_for_testing):
        label1 = Label.objects.create(name="L1", color="#111111", owner=owner)
        
        updated_task, updated = task_update_service(
            task_id=task_for_testing.id,
            user=owner,
            labels=[label1.id]
        )
        
        assert updated
        assert updated_task.labels.count() == 1
        assert label1 in updated_task.labels.all()

    def test_get_tasks_by_label(self, owner):
        label = Label.objects.create(name="Filtered", color="#000000", owner=owner)
        task1 = task_add_service(title="T1", description="D1", owner=owner, labels=[label.id])
        task2 = task_add_service(title="T2", description="D2", owner=owner)
        
        tasks_with_label = get_tasks_by_label(user=owner, label_id=label.id)
        
        assert task1 in tasks_with_label
        assert task2 not in tasks_with_label
        assert tasks_with_label.count() == 1
