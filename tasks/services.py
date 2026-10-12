from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .exceptions import DueDateInPastError, ScheduledDateInPastError
from .models import Task
from .reminder_types import (
    TYPE_DUE_SOON,
    TYPE_DUE_TODAY,
    TYPE_OVERDUE,
    TYPE_SCHEDULED_TODAY,
)
from .selectors import get_task_for_user
from notifications.models import Notification
from notifications.selectors import invalidate_unread_notifications_count

User = settings.AUTH_USER_MODEL

REMINDER_NOTIFICATION_TYPES = [
    TYPE_DUE_TODAY,
    TYPE_DUE_SOON,
    TYPE_OVERDUE,
    TYPE_SCHEDULED_TODAY,
]


class _Unset(Enum):
    """Enum token used as the ``UNSET`` sentinel (narrowable via ``is`` checks)."""

    VALUE = "unset"


UNSET = _Unset.VALUE
"""Default marker for optional update arguments: ``None`` clears, ``UNSET`` skips."""


def _clear_task_reminder_notifications(task: Task) -> None:
    """Delete generated reminder notifications for a task (so they regenerate)."""
    deleted = Notification.objects.filter(
        target_content_type=ContentType.objects.get_for_model(Task),
        target_object_id=task.pk,
        type__in=REMINDER_NOTIFICATION_TYPES,
    ).delete()
    if deleted[0]:
        invalidate_unread_notifications_count(user_id=task.owner.pk)


# -- Helper Functions -- #
def status_check(status: str, task: Task) -> bool:
    """Validate ``status`` and report whether it differs from the task's current one."""
    if status not in Task.Status.values:
        raise ValueError(f"'{status}' is not a valid status.")
    return task.status != status


def scheduled_date_check(scheduled_date: date, task: Task):
    if task.scheduled_date != scheduled_date:
        if scheduled_date < timezone.now().date():
            raise ScheduledDateInPastError("The scheduled date cannot be in the past.")
        return True
    return False


def priority_check(priority: int, task: Task) -> bool:
    """Validate ``priority`` and report whether it differs from the current one."""
    if priority not in Task.Priority.values:
        raise ValueError(f"'{priority}' is not a valid priority.")
    return task.priority != priority


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
    status: str = Task.Status.TODO,
    priority: int = Task.Priority.MEDIUM,
    due_datetime: datetime | None = None,
    scheduled_date: date | None = None,
    owner: User,
    labels: list[int] | None = None,
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
        labels: An optional list of label IDs to associate with the task.

    Returns:
        The newly created Task instance.

    Raises:
        DueDateInPastError: If the provided due_datetime is in the past.
        ValueError: If ``status`` or ``priority`` is not a valid choice.
    """
    today = timezone.now().date()
    if due_datetime and due_datetime.date() < today:
        raise DueDateInPastError("Due date cannot be in the past.")
    if status not in Task.Status.values:
        raise ValueError(f"'{status}' is not a valid status.")
    if priority not in Task.Priority.values:
        raise ValueError(f"'{priority}' is not a valid priority.")

    todo_item = Task.objects.create(
        title=title,
        description=description or "",
        status=status,
        priority=priority,
        due_datetime=due_datetime,
        scheduled_date=scheduled_date,
        owner=owner,
    )
    if labels:
        todo_item.labels.set(labels)
    return todo_item


@transaction.atomic
def toggle_task_status_service(*, task: Task) -> Task:
    """
    Toggles a task between TODO and COMPLETED.

    The quick toggle is intentionally a two-state switch (TODO <-> COMPLETED);
    the intermediate statuses (IN_PROGRESS, ON_HOLD) are only reachable when
    editing the task. Any non-completed status advances to COMPLETED;
    COMPLETED returns to TODO.

    Args:
        task: The Task instance to be updated.

    Returns:
        The updated Task instance with the new status.
    """
    if task.status == Task.Status.COMPLETED:
        task.status = Task.Status.TODO
    else:
        task.status = Task.Status.COMPLETED
        # A completed task should stop being nagged; the beat job will not
        # regenerate reminders for it.
        _clear_task_reminder_notifications(task)
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
    due_datetime: datetime | None | _Unset = UNSET,
    scheduled_date: date | None | _Unset = UNSET,
    labels: list[int] | None = None,
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
        due_datetime: The new due datetime, if provided; ``None`` clears it,
            ``UNSET`` (the default) leaves it unchanged.
        scheduled_date: The new scheduled date, if provided; ``None`` clears it,
            ``UNSET`` (the default) leaves it unchanged.
        labels: The new list of label IDs, if provided.

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
    updated = False
    if title is not None and task.title != title:
        task.title = title
        fields_to_update.append("title")

    if description is not None and task.description != description:
        task.description = description
        fields_to_update.append("description")

    if status is not None and status_check(status=status, task=task):
        task.status = status
        fields_to_update.append("status")

    if priority is not None and priority_check(priority=priority, task=task):
        task.priority = priority
        fields_to_update.append("priority")

    if due_datetime is not UNSET:
        if due_datetime is None:
            if task.due_datetime is not None:
                task.due_datetime = None
                fields_to_update.append("due_datetime")
        elif due_datetime_check(due_datetime=due_datetime, task=task):
            task.due_datetime = due_datetime
            fields_to_update.append("due_datetime")

    if scheduled_date is not UNSET:
        if scheduled_date is None:
            if task.scheduled_date is not None:
                task.scheduled_date = None
                fields_to_update.append("scheduled_date")
        elif scheduled_date_check(scheduled_date=scheduled_date, task=task):
            task.scheduled_date = scheduled_date
            fields_to_update.append("scheduled_date")

    if fields_to_update:
        task.save(update_fields=fields_to_update)
        updated = True

    if labels is not None:
        task.labels.set(labels)
        updated = True

    reminders_stale = any(
        field in fields_to_update
        for field in ("title", "due_datetime", "scheduled_date")
    ) or ("status" in fields_to_update and task.status == Task.Status.COMPLETED)
    if updated and reminders_stale:
        # A title or date change invalidates previously generated reminders
        # (stale message text / stale dates); the next beat run will
        # regenerate them for the current task state. Completing the task
        # must stop the nagging, matching the quick-toggle behavior.
        _clear_task_reminder_notifications(task)

    return task, updated


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
