from django.utils import timezone
from django.test import TestCase
from todo.exceptions import DueDateInPastError
from todo.models import Task
from accounts.models import User
from todo.services import add_task_service


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
        task_item = add_task_service(
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
            add_task_service(
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
        # was created in the database. This is a very important check!
        self.assertEqual(Task.objects.count(), 0)
