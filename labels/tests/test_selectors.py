import pytest

from labels.models import Label


@pytest.mark.django_db
class TestLabelSelector:
    def test_get_label_with_pk(self, label_selector, labels):
        label = labels[0]
        fetched_label = label_selector.get_label(pk=label.pk)
        assert fetched_label == label

    def test_get_labels(self, label_selector, labels):
        fetched_labels = label_selector.get_labels()
        assert fetched_labels.count() == len(labels)
        for label in labels:
            assert label in fetched_labels

    def test_get_labels_ordered_by_name(self, user, label_selector):
        for name in ("zeta", "alpha", "beta"):
            Label.objects.create(name=name, color="#000000", owner=user)

        names = list(label_selector.get_labels().values_list("name", flat=True))

        assert names == ["alpha", "beta", "zeta"]

    def test_get_label_belongs_to_other_user(
        self, label_selector, labels, django_user_model
    ):
        other_user = django_user_model.objects.create_user(username="otheruser")
        other_label = Label.objects.create(
            name="Other", color="#000000", owner=other_user
        )

        with pytest.raises(Label.DoesNotExist):
            label_selector.get_label(pk=other_label.pk)

        fetched_labels = label_selector.get_labels()
        assert other_label not in fetched_labels
