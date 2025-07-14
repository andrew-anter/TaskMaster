from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .exceptions import DueDateInPastError
from .models import Task
from .services import task_add_service, toggle_task_status_service


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


# TODO: test for updating task service
# TODO: test for deleting task service
