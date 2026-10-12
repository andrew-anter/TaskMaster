import pytest
from django.utils import timezone
from datetime import datetime

from notifications.models import Notification
from notifications.services import notify

from ..exceptions import DueDateInPastError
from ..models import Task
from ..services import (
    task_add_service,
    toggle_task_status_service,
    task_update_service,
    task_delete_service,
)


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

    def test_create_defaults_status_to_todo(self, valid_task_data):
        """A task created without an explicit status starts as TODO."""
        data = {key: value for key, value in valid_task_data.items() if key != "status"}

        task_item = task_add_service(**data)

        assert task_item.status == Task.Status.TODO

    def test_create_task_with_invalid_status_raises(self, valid_task_data):
        """An unknown status is rejected and no task is created."""
        invalid_data = {**valid_task_data, "status": "ARCHIVED"}

        with pytest.raises(ValueError):
            task_add_service(**invalid_data)

        assert Task.objects.count() == 0

    def test_create_task_with_invalid_priority_raises(self, valid_task_data):
        """An unknown priority is rejected and no task is created."""
        invalid_data = {**valid_task_data, "priority": 99}

        with pytest.raises(ValueError):
            task_add_service(**invalid_data)

        assert Task.objects.count() == 0


@pytest.mark.django_db
class TestToggleTaskStatusService:
    def test_toggle_advances_todo_to_completed(self, todo_task):
        """
        Tests that a task with status 'TODO' advances to 'COMPLETED'.
        """
        task = todo_task

        toggle_task_status_service(task=task)
        task.refresh_from_db()

        assert task.status == Task.Status.COMPLETED

    def test_toggle_advances_in_progress_to_completed(self, in_progress_task):
        """
        Tests that a task with status 'IN_PROGRESS' advances to 'COMPLETED'.
        """
        task = in_progress_task

        toggle_task_status_service(task=task)
        task.refresh_from_db()

        assert task.status == Task.Status.COMPLETED

    def test_toggle_advances_on_hold_to_completed(self, on_hold_task):
        """
        Tests that a task with status 'ON_HOLD' advances to 'COMPLETED'.
        """
        task = on_hold_task

        toggle_task_status_service(task=task)
        task.refresh_from_db()

        assert task.status == Task.Status.COMPLETED

    def test_toggle_completed_back_to_todo(self, completed_task):
        """
        Tests that a task with status 'COMPLETED' returns to 'TODO'.
        """
        task = completed_task

        toggle_task_status_service(task=task)
        task.refresh_from_db()

        assert task.status == Task.Status.TODO

    def test_unknown_status_advances_to_completed(self, owner):
        """
        A status outside the choices (e.g. written via shell/admin) is treated
        as a non-completed status and advances to 'COMPLETED' rather than
        raising.
        """
        task = Task.objects.create(owner=owner, title="Weird", status="ARCHIVED")

        toggle_task_status_service(task=task)
        task.refresh_from_db()

        assert task.status == Task.Status.COMPLETED


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

    def test_clear_title_with_empty_string(self, task_for_testing):
        """Tests that passing an empty string clears the title."""
        task = task_for_testing
        assert task.title != ""

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            title="",
        )

        task.refresh_from_db()
        assert task.title == ""
        assert updated is True

    def test_clear_due_datetime_with_none(self, task_for_testing):
        """Passing ``None`` explicitly clears the due datetime."""
        task = task_for_testing
        assert task.due_datetime is not None

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            due_datetime=None,
        )

        task.refresh_from_db()
        assert task.due_datetime is None
        assert updated is True

    def test_clear_scheduled_date_with_none(self, task_for_testing):
        """Passing ``None`` explicitly clears the scheduled date."""
        task = task_for_testing
        assert task.scheduled_date is not None

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            scheduled_date=None,
        )

        task.refresh_from_db()
        assert task.scheduled_date is None
        assert updated is True

    def test_omitted_dates_are_left_unchanged(self, task_for_testing):
        """Omitting the date arguments leaves existing values intact."""
        task = task_for_testing
        original_due = task.due_datetime
        original_scheduled = task.scheduled_date

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            title="Only the title changed",
        )

        task.refresh_from_db()
        assert task.due_datetime == original_due
        assert task.scheduled_date == original_scheduled
        assert updated is True

    def test_invalid_status_raises_even_when_unchanged(self, owner):
        """A stored invalid status is still rejected on a no-op update."""
        task = Task.objects.create(owner=owner, title="Weird", status="ARCHIVED")

        with pytest.raises(ValueError):
            task_update_service(task_id=task.pk, user=owner, status="ARCHIVED")

    def test_invalid_priority_raises_even_when_unchanged(self, owner):
        """A stored invalid priority is still rejected on a no-op update."""
        task = Task.objects.create(owner=owner, title="Weird priority", priority=99)

        with pytest.raises(ValueError):
            task_update_service(task_id=task.pk, user=owner, priority=99)

    def test_set_priority_to_none_value(self, task_for_testing):
        """Priority NONE (0) is valid and must not be skipped as falsy."""
        task = task_for_testing

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            priority=Task.Priority.NONE,
        )

        task.refresh_from_db()
        assert task.priority == Task.Priority.NONE
        assert updated is True

    def test_clearing_already_empty_date_reports_no_update(self, task_for_testing):
        """Clearing a date that is already empty is a no-op, not a change."""
        task = task_for_testing
        task_update_service(task_id=task.pk, user=task.owner, due_datetime=None)
        task.refresh_from_db()
        assert task.due_datetime is None

        _, updated = task_update_service(
            task_id=task.pk, user=task.owner, due_datetime=None
        )

        assert updated is False

    def test_completing_task_clears_reminder_notifications(self, task_for_testing):
        """Marking a task COMPLETED through the update service stops reminders."""
        task = task_for_testing
        notify(
            recipient=task.owner,
            type="task_overdue",
            message="Overdue reminder",
            target=task,
        )
        assert Notification.objects.filter(target_object_id=task.pk).exists()

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            status=Task.Status.COMPLETED,
        )

        assert updated is True
        assert not Notification.objects.filter(target_object_id=task.pk).exists()

    def test_clear_description_with_empty_string(self, task_for_testing):
        """Tests that passing an empty string clears the description."""
        task = task_for_testing
        assert task.description != ""

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            description="",
        )

        task.refresh_from_db()
        assert task.description == ""
        assert updated is True

    def test_none_does_not_overwrite_existing_title(self, task_for_testing):
        """Tests that passing None leaves the title unchanged."""
        task = task_for_testing
        original_title = task.title

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            title=None,
        )

        task.refresh_from_db()
        assert task.title == original_title

    def test_none_does_not_overwrite_existing_description(self, task_for_testing):
        """Tests that passing None leaves the description unchanged."""
        task = task_for_testing
        original_description = task.description

        task, updated = task_update_service(
            task_id=task.pk,
            user=task.owner,
            description=None,
        )

        task.refresh_from_db()
        assert task.description == original_description


@pytest.mark.django_db
class TestDeleteTaskService:
    def test_delete_task(self, task_for_testing, owner):
        task_id = task_for_testing.pk
        user = owner

        task_delete_service(user=user, task_id=task_id)
        with pytest.raises(Task.DoesNotExist):
            Task.objects.get(pk=task_id)
