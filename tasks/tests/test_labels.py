import pytest

from accounts.models import User
from labels.models import Label
from tasks.models import Task
from tasks.selectors import get_tasks_by_label
from tasks.services import task_add_service, task_update_service


@pytest.mark.django_db
class TestTaskLabels:
    def test_add_task_with_labels(self, owner):
        label1 = Label.objects.create(name="L1", color="#111111", owner=owner)
        label2 = Label.objects.create(name="L2", color="#222222", owner=owner)

        task = task_add_service(
            title="Task with labels",
            description="Desc",
            owner=owner,
            labels=[label1.pk, label2.pk],
        )

        assert task.labels.count() == 2
        assert label1 in task.labels.all()
        assert label2 in task.labels.all()

    def test_add_accepts_label_instances(self, owner):
        """The web form passes ``Label`` instances, not primary keys."""
        label = Label.objects.create(name="L1", color="#111111", owner=owner)

        task = task_add_service(
            title="Task with labels",
            description="Desc",
            owner=owner,
            labels=[label],
        )

        assert list(task.labels.all()) == [label]

    def test_duplicate_label_pks_are_deduplicated(self, owner):
        """Repeating a pk must not look like a missing label."""
        label = Label.objects.create(name="L1", color="#111111", owner=owner)

        task = task_add_service(
            title="Task with labels",
            description="Desc",
            owner=owner,
            labels=[label.pk, label.pk],
        )

        assert task.labels.count() == 1

    def test_add_with_foreign_label_raises(self, owner):
        """Another user's label cannot be attached to a task."""
        other = User.objects.create_user(username="labelintruder", password="pass12345")
        foreign = Label.objects.create(name="Theirs", color="#333333", owner=other)

        with pytest.raises(ValueError):
            task_add_service(
                title="Sneaky",
                description="",
                owner=owner,
                labels=[foreign.pk],
            )

        assert not Task.objects.filter(owner=owner).exists()

    def test_update_with_foreign_label_raises(self, owner, task_for_testing):
        """Another user's label cannot be attached through an update either."""
        other = User.objects.create_user(username="labelintruder", password="pass12345")
        foreign = Label.objects.create(name="Theirs", color="#333333", owner=other)

        with pytest.raises(ValueError):
            task_update_service(
                task_id=task_for_testing.pk, user=owner, labels=[foreign.pk]
            )

        assert task_for_testing.labels.count() == 0

    def test_update_accepts_label_instances_as_no_change(self, owner):
        """A form QuerySet of unchanged labels is a no-op, not a change."""
        label = Label.objects.create(name="L1", color="#111111", owner=owner)
        task = Task.objects.create(owner=owner, title="Labelled")
        task.labels.set([label.pk])

        task, updated = task_update_service(
            task_id=task.pk,
            user=owner,
            labels=Label.objects.filter(owner=owner),
        )

        assert updated is False
        assert list(task.labels.values_list("pk", flat=True)) == [label.pk]

    def test_update_task_labels(self, owner, task_for_testing):
        label1 = Label.objects.create(name="L1", color="#111111", owner=owner)

        updated_task, updated = task_update_service(
            task_id=task_for_testing.id, user=owner, labels=[label1.pk]
        )

        assert updated
        assert updated_task.labels.count() == 1
        assert label1 in updated_task.labels.all()

    def test_get_tasks_by_label(self, owner):
        label = Label.objects.create(name="Filtered", color="#000000", owner=owner)
        task1 = task_add_service(
            title="T1", description="D1", owner=owner, labels=[label.pk]
        )
        task2 = task_add_service(title="T2", description="D2", owner=owner)

        tasks_with_label = get_tasks_by_label(user=owner, label_id=label.pk)

        assert task1 in tasks_with_label
        assert task2 not in tasks_with_label
        assert tasks_with_label.count() == 1
