from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .exceptions import DueDateInPastError, ScheduledDateInPastError
from .models import Task
from .selectors import get_task_for_user

User = settings.AUTH_USER_MODEL


# -- Helper Functions -- #
def status_check(status: str, task: Task):
    if task.status != status:
        if status not in [choice[0] for choice in Task.Status.choices]:
            raise ValueError(f"'{status}' is not a valid status.")
        return True
    return False


def scheduled_date_check(scheduled_date: date, task: Task):
    if task.scheduled_date != scheduled_date:
        if scheduled_date < timezone.now().date():
            raise ScheduledDateInPastError("The scheduled date cannot be in the past.")
        return True
    return False


def priority_check(priority: int, task: Task):
    if task.priority != priority:
        if priority not in [choice[0] for choice in Task.Priority.choices]:
            raise ValueError(f"'{priority}' is not a valid priority.")
        return True
    return False


def due_datetime_check(due_datetime: datetime, task: Task):
    if task.due_datetime != due_datetime:
        if due_datetime.tzinfo is None:
            due_datetime = timezone.make_aware(due_datetime)
        if due_datetime < timezone.now():
            raise DueDateInPastError("The due date cannot be in the past.")
        return True
    return False


@transaction.atomic
def task_add_service(
    *,
    title: str,
    description: str | None,
    status: str = Task.Status.IN_PROGRESS,
    priority: int = Task.Priority.MEDIUM,
    due_datetime: datetime | None = None,
    scheduled_date: date | None = None,
    owner: User,
) -> Task:
    """
    Creates a new task with the provided details.

    This service handles the business logic of creating a new task, including
    initial validation. It is wrapped in a transaction to ensure atomicity.

    Args:
        title: The title of the task.
        description: An optional longer description for the task.
        status: The initial status (e.g., 'TODO', 'IN_PROGRESS').
        priority: The priority level of the task.
        due_datetime: An optional datetime for when the task is due.
        scheduled_date: An optional date for when to work on the task.
        owner: The user who owns this task.

    Returns:
        The newly created Task instance.

    Raises:
        DueDateInPastError: If the provided due_datetime is in the past.
        # Note: Further validation for status, priority, etc., could be added here.
    """
    today = timezone.now().date()
    if due_datetime and due_datetime.date() < today:
        raise DueDateInPastError("Due date cannot be in the past.")

    todo_item = Task.objects.create(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_datetime=due_datetime,
        scheduled_date=scheduled_date,
        owner=owner,
    )
    return todo_item


@transaction.atomic
def toggle_task_status_service(*, task: Task) -> Task:
    """
    Toggles a task's status between 'TODO' and 'COMPLETED'.

    Args:
        task: The Task instance to be updated.

    Returns:
        The updated Task instance with the new status.
    """
    if task.status == Task.Status.COMPLETED:
        task.status = Task.Status.TODO
    else:
        task.status = Task.Status.COMPLETED
    task.save(update_fields=["status"])
    return task


@transaction.atomic
def task_update_service(
    *,
    task_id: int,
    user: User,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    due_datetime: datetime | None = None,
    scheduled_date: date | None = None,
) -> tuple[Task, bool]:
    """
    Updates a task with the provided values, performing a partial update.

    This service fetches the relevant task, validates user ownership, and then
    updates only the fields that are provided (not None). It reports back
    whether any fields were actually changed.

    Args:
        task_id: The ID of the task to update.
        user: The user performing the update, for permission checking.
        title: The new title, if provided.
        description: The new description, if provided.
        status: The new status, if provided.
        priority: The new priority, if provided.
        due_datetime: The new due datetime, if provided.
        scheduled_date: The new scheduled date, if provided.

    Returns:
        A tuple containing:
            - task (Task): The updated task instance.
            - updated (bool): True if any fields were changed, False otherwise.

    Raises:
        Task.DoesNotExist: If the task_id does not exist for the given user.
        ValueError: If the provided status or priority is not a valid choice.
        DueDateInPastError: If the provided due_datetime is in the past.
        ScheduledDateInPastError: If the provided scheduled_date is in the past.
    """

    task = get_task_for_user(user=user, task_id=task_id)

    fields_to_update = []
    if title and task.title != title:
        task.title = title
        fields_to_update.append("title")

    if description and task.description != description:
        task.description = description
        fields_to_update.append("description")

    if status and status_check(status=status, task=task):
        task.status = status
        fields_to_update.append("status")

    if priority and priority_check(priority=priority, task=task):
        task.priority = priority
        fields_to_update.append("priority")

    if due_datetime and due_datetime_check(due_datetime=due_datetime, task=task):
        task.due_datetime = due_datetime
        fields_to_update.append("due_datetime")

    if scheduled_date and scheduled_date_check(
        scheduled_date=scheduled_date, task=task
    ):
        task.scheduled_date = scheduled_date
        fields_to_update.append("scheduled_date")

    if fields_to_update:
        task.save(update_fields=fields_to_update)
        return task, True

    return task, False


@transaction.atomic
def task_delete_service(*, user: User, task_id: int) -> None:
    """
    Deletes a task after verifying ownership.

    Note:
        This service follows a "succeed or raise" pattern. It returns nothing
        (None) on success. If the task cannot be found for the user, the
        underlying `get_task_for_user` will raise `Task.DoesNotExist`, which
        should be handled by the calling view.

    Args:
        user: The user performing the delete action.
        task_id: The ID of the task to be deleted.

    Returns:
        None on success.

    Raises:
        Task.DoesNotExist: If the task does not exist for the user.
    """
    task = get_task_for_user(user=user, task_id=task_id)
    _ = task.delete()
