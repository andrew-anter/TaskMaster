import pytest
from django.test import TestCase
from django.utils import timezone

from datetime import datetime
from accounts.models import User
from .exceptions import DueDateInPastError
from .models import Task
from .services import task_add_service, toggle_task_status_service, task_update_service


class AddTaskServiceTestCase(TestCase):
    def setUp(self):
        self.title = "Test title"
        self.description = "Test Description"
        self.status = Task.Status.IN_PROGRESS
        self.priority = Task.Priority.MEDIUM
        self.due_datetime = timezone.now()
        self.scheduled_date = timezone.now().date()
        self.owner, _ = User.objects.get_or_create(username="testuser")

    def test_create_task_with_valid_data(self):
        task_item = task_add_service(
            title=self.title,
            description=self.description,
            status=self.status,
            priority=self.priority,
            due_datetime=self.due_datetime,
            scheduled_date=self.scheduled_date,
            owner=self.owner,
        )

        # Task was added to db check
        self.assertTrue(Task.objects.filter(pk=task_item.pk).exists())

        # Data is valid check
        self.assertEqual(task_item.title, self.title)
        self.assertEqual(task_item.description, self.description)
        self.assertEqual(task_item.status, self.status)
        self.assertEqual(task_item.priority, self.priority)
        self.assertEqual(task_item.due_datetime, self.due_datetime)
        self.assertEqual(task_item.scheduled_date, self.scheduled_date)
        self.assertEqual(task_item.owner, self.owner)

    def test_create_task_with_invalid_duedatetime(self):
        past_due_datetime = timezone.now() - timezone.timedelta(days=10)  # type:ignore
        with self.assertRaises(DueDateInPastError):
            task_add_service(
                title=self.title,
                description=self.description,
                status=self.status,
                priority=self.priority,
                due_datetime=past_due_datetime,
                scheduled_date=self.scheduled_date,
                owner=self.owner,
            )

        # --- Assert for Side Effects ---
        # After confirming the exception was raised, we assert that NO task
        # was created in the database.
        self.assertEqual(Task.objects.count(), 0)


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


@pytest.fixture
def task_for_testing() -> Task:
    """
    A pytest fixture that creates a default Task instance for use in tests.
    This replaces the old setUp method.
    """
    owner, _ = User.objects.get_or_create(username="testuser")
    task = task_add_service(
        title="Original Title",
        description="Original Description",
        status=Task.Status.IN_PROGRESS,
        priority=Task.Priority.MEDIUM,
        due_datetime=timezone.now(),
        scheduled_date=timezone.now().date(),
        owner=owner,
    )
    return task


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
