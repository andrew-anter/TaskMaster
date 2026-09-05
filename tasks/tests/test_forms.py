import pytest

from accounts.models import User
from labels.forms import LabelForm, LABEL_COLORS
from labels.models import Label
from tasks.forms import TaskForm
from tasks.models import Task


@pytest.fixture
def user():
    return User.objects.create_user(username="formtester", password="testpass1234")


@pytest.mark.django_db
class TestTaskForm:
    def test_valid_data(self, user):
        data = {
            "title": "Test Task",
            "description": "A description",
            "status": Task.Status.TODO,
            "priority": Task.Priority.MEDIUM,
        }
        form = TaskForm(data=data, user=user)
        assert form.is_valid()

    def test_empty_title_invalid(self, user):
        data = {
            "title": "",
            "status": Task.Status.TODO,
            "priority": Task.Priority.MEDIUM,
        }
        form = TaskForm(data=data, user=user)
        assert not form.is_valid()
        assert "title" in form.errors

    def test_invalid_status_invalid(self, user):
        data = {
            "title": "Task",
            "status": "INVALID_STATUS",
            "priority": Task.Priority.MEDIUM,
        }
        form = TaskForm(data=data, user=user)
        assert not form.is_valid()

    def test_labels_filtered_to_user(self, user):
        other_user = User.objects.create_user(username="other", password="pass1234")
        Label.objects.create(name="Mine", color="#000000", owner=user)
        Label.objects.create(name="Theirs", color="#111111", owner=other_user)
        form = TaskForm(user=user)
        label_ids = list(form.fields["labels"].queryset.values_list("pk", flat=True))
        assert len(label_ids) == 1

    def test_valid_datetime_fields(self, user):
        data = {
            "title": "Task with dates",
            "status": Task.Status.TODO,
            "priority": Task.Priority.LOW,
            "due_datetime": "2077-12-31T23:59",
            "scheduled_date": "2077-12-31",
        }
        form = TaskForm(data=data, user=user)
        assert form.is_valid()


@pytest.mark.django_db
class TestLabelForm:
    def test_valid_data(self):
        data = {"name": "Bug", "color": "#EF4444"}
        form = LabelForm(data=data)
        assert form.is_valid()

    def test_empty_name_invalid(self):
        data = {"name": "", "color": "#EF4444"}
        form = LabelForm(data=data)
        assert not form.is_valid()
        assert "name" in form.errors

    def test_invalid_color_invalid(self):
        data = {"name": "Test", "color": "#ZZZZZZ"}
        form = LabelForm(data=data)
        assert not form.is_valid()
        assert "color" in form.errors

    def test_all_valid_colors_accepted(self):
        for color in LABEL_COLORS:
            data = {"name": f"Label {color}", "color": color}
            form = LabelForm(data=data)
            assert form.is_valid(), f"Color {color} should be valid"
