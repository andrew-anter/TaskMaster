import pytest


@pytest.mark.django_db
class TestLabelSelector:
    def test_get_label_with_pk(self, label_selector, labels):
        label_selector.get_label(pk=1)

    def test_get_labels(self, label_selector, labels):
        label_selector.get_labels(ids=[1, 2])

    def test_get_labels_for_task(self, label_selector, task, labels):
        labels_from_selector_ids = list(
            label_selector.get_labels_for_task(task_id=task.pk).values_list(
                "pk", flat=True
            )
        )
        labels_ids = [label.pk for label in labels]

        assert labels_ids == labels_from_selector_ids
