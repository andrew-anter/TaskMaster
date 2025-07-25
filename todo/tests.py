import pytest
from django.test import TestCase
from django.utils import timezone

from .exceptions import DueDateInPastError
from datetime import datetime
from accounts.models import User
from .models import Task
from .services import task_add_service, toggle_task_status_service, task_update_service


@pytest.fixture
def owner() -> User:
    """Fixture to provide a user object for tests."""
    user, _ = User.objects.get_or_create(username="testuser")
    return user


@pytest.fixture
def valid_task_data(owner: User) -> dict:
    """Fixture to provide a dictionary of valid data for creating a task."""
    return {
        "title": "Test title",
        "description": "Test Description",
        "status": Task.Status.IN_PROGRESS,
        "priority": Task.Priority.MEDIUM,
        "due_datetime": timezone.now(),
        "scheduled_date": timezone.now().date(),
        "owner": owner,
    }


@pytest.fixture
def task_for_testing(valid_task_data: dict) -> Task:
    """
    This fixture now DEPENDS on the 'valid_task_data' fixture.
    Pytest will run 'valid_task_data' first and pass its result in.
    """
    task = task_add_service(**valid_task_data)
    return task


@pytest.mark.django_db
class TestAddTaskService:
    def test_create_task_with_valid_data(self, valid_task_data):
        """Tests that a task is created correctly with valid data."""
        task_item = task_add_service(**valid_task_data)

        assert Task.objects.filter(pk=task_item.pk).exists()
        for key, value in valid_task_data.items():
            assert getattr(task_item, key) == value

    def test_create_task_with_invalid_duedatetime(self, valid_task_data):
        """
        Tests that a custom exception is raised for a past due date
        and that no task is created.
        """
        invalid_data = valid_task_data.copy()
        invalid_data["due_datetime"] = timezone.now() - timezone.timedelta(days=10)

        # Act & Assert for the exception
        with pytest.raises(DueDateInPastError):
            task_add_service(**invalid_data)

        # Assert for side effects (that no task was created)
        assert Task.objects.count() == 0


class ToggleTaskStatusServiceTestCase(TestCase):
    def setUp(self):
        title = "Test title"
        description = "Test Description"
        status = Task.Status.IN_PROGRESS
        priority = Task.Priority.MEDIUM
        due_datetime = timezone.now()
        scheduled_date = timezone.now().date()
        owner, _ = User.objects.get_or_create(username="testuser")

        self.task = task_add_service(
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_datetime=due_datetime,
            scheduled_date=scheduled_date,
            owner=owner,
        )

    def test_toggling_between_completed_and_todo(self):
        task = toggle_task_status_service(task=self.task)
        self.task.refresh_from_db()
        self.assertEqual(task, self.task)

        toggle_task_status_service(task=self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)

        toggle_task_status_service(task=self.task)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)


@pytest.mark.django_db
class TestUpdateTaskService:
    """
    A class to group all tests related to the task_update_service.
    """

    def test_update_text_fields(self, task_for_testing):
        """Tests that title and description fields are updated correctly."""
        task = task_for_testing
        new_title = "new test title"
        new_description = "new test Description"

        task_update_service(
            task_id=task.pk,
            user=task.owner,
            title=new_title,
            description=new_description,
        )

        task.refresh_from_db()
        assert task.title == new_title
        assert task.description == new_description

    def test_update_choice_fields(self, task_for_testing):
        """Tests that status and priority fields are updated correctly."""
        task = task_for_testing
        new_status = Task.Status.ON_HOLD
        new_priority = Task.Priority.HIGH

        task_update_service(
            task_id=task.pk,
            user=task.owner,
            status=new_status,
            priority=new_priority,
        )

        task.refresh_from_db()
        assert task.status == new_status
        assert task.priority == new_priority

    def test_update_datetime_fields(self, task_for_testing):
        """Tests that date-related fields are updated correctly."""
        task = task_for_testing
        datetime_str = "2077-01-01 14:14:14"
        format_code = "%Y-%m-%d %H:%M:%S"

        aware_datetime = timezone.make_aware(
            datetime.strptime(datetime_str, format_code)
        )
        new_scheduled_date = aware_datetime.date()

        task_update_service(
            task_id=task.pk,
            user=task.owner,
            due_datetime=aware_datetime,
            scheduled_date=new_scheduled_date,
        )

        task.refresh_from_db()
        assert task.due_datetime == aware_datetime
        assert task.scheduled_date == new_scheduled_date


# TODO: test for deleting task service
