from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from enum import Enum

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from labels.models import Label
from notifications.models import Notification
from notifications.selectors import invalidate_unread_notifications_count

from .exceptions import DueDateInPastError, ScheduledDateInPastError
from .models import Task
from .reminder_types import (
    TYPE_DUE_SOON,
    TYPE_DUE_TODAY,
    TYPE_OVERDUE,
    TYPE_SCHEDULED_TODAY,
)
from .selectors import get_task_for_user

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


def _due_date_in_past(due_datetime: datetime) -> bool:
    """
    Report whether ``due_datetime`` falls on a day before today.

    Creation and updates share one date-level rule: a time earlier today is
    still "today", so it is accepted (the dashboard only calls a task overdue
    once its day has passed).
    """
    if due_datetime.tzinfo is None:
        due_datetime = timezone.make_aware(due_datetime)
    return due_datetime.date() < timezone.now().date()


def _validated_label_pks(*, labels: Iterable[Label | int], owner: User) -> list[int]:
    """
    Normalize ``labels`` to a sorted, deduplicated list of primary keys.

    Callers pass ``Label`` instances (the web form's QuerySet) or plain primary
    keys (the API), so both shapes are normalized before use. A single
    ownership query enforces the tenant boundary before ``.set()`` runs.

    Raises:
        ValueError: If any label does not exist or belongs to another user.
    """
    pks = sorted({label.pk if isinstance(label, Label) else label for label in labels})
    owned = set(
        Label.objects.filter(pk__in=pks, owner=owner).values_list("pk", flat=True)
    )
    if owned != set(pks):
        raise ValueError("One or more labels do not belong to this user.")
    return pks


def clear_reminder_notifications_for_tasks(*, pks: Iterable[int]) -> int:
    """
    Delete generated reminder notifications for several tasks at once.

    Bulk admin actions bypass the per-task services, so they need this to stop
    stale "Overdue"/"Due Today" reminders. Row-level deletes fire the central
    ``post_delete`` signal, which invalidates the recipients' unread counts.

    Returns:
        The number of deleted notifications.
    """
    deleted, _ = Notification.objects.filter(
        target_content_type=ContentType.objects.get_for_model(Task),
        target_object_id__in=list(pks),
        type__in=REMINDER_NOTIFICATION_TYPES,
    ).delete()
    return deleted


def _clear_task_reminder_notifications(task: Task) -> None:
    """Delete generated reminder notifications for a task (so they regenerate)."""
    if clear_reminder_notifications_for_tasks(pks=[task.pk]):
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
        if _due_date_in_past(due_datetime):
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
    labels: Iterable[Label | int] | None = None,
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
        labels: An optional iterable of labels (``Label`` instances or primary
            keys) to associate with the task; all must belong to ``owner``.

    Returns:
        The newly created Task instance.

    Raises:
        DueDateInPastError: If the provided due_datetime is in the past.
        ScheduledDateInPastError: If the provided scheduled_date is in the past.
        ValueError: If ``status`` or ``priority`` is not a valid choice, or a
            label does not belong to ``owner``.
    """
    today = timezone.now().date()
    if due_datetime and _due_date_in_past(due_datetime):
        raise DueDateInPastError("Due date cannot be in the past.")
    if scheduled_date and scheduled_date < today:
        raise ScheduledDateInPastError("The scheduled date cannot be in the past.")
    if status not in Task.Status.values:
        raise ValueError(f"'{status}' is not a valid status.")
    if priority not in Task.Priority.values:
        raise ValueError(f"'{priority}' is not a valid priority.")
    label_pks: list[int] = []
    if labels is not None:
        label_pks = _validated_label_pks(labels=labels, owner=owner)

    todo_item = Task.objects.create(
        title=title,
        description=description or "",
        status=status,
        priority=priority,
        due_datetime=due_datetime,
        scheduled_date=scheduled_date,
        owner=owner,
    )
    if label_pks:
        todo_item.labels.set(label_pks)
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
    # Re-read under a row lock so two concurrent toggles cannot both compute
    # from the same status and lose one flip (SQLite ignores FOR UPDATE; the
    # lock is effective on PostgreSQL).
    task = Task.objects.select_for_update().get(pk=task.pk)
    if task.status == Task.Status.COMPLETED:
        task.status = Task.Status.TODO
    else:
        task.status = Task.Status.COMPLETED
        # A completed task should stop being nagged; the beat job will not
        # regenerate reminders for it.
        _clear_task_reminder_notifications(task)
    task.save(update_fields=["status", "modified_at"])
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
    due_datetime: datetime | _Unset | None = UNSET,
    scheduled_date: date | _Unset | None = UNSET,
    labels: Iterable[Label | int] | None = None,
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
        labels: The new set of labels (``Label`` instances or primary keys), if
            provided; all must belong to ``user``.

    Returns:
        A tuple containing:
            - task (Task): The updated task instance.
            - updated (bool): True if any fields were changed, False otherwise.

    Raises:
        Task.DoesNotExist: If the task_id does not exist for the given user.
        ValueError: If the provided status or priority is not a valid choice,
            or a label does not belong to ``user``.
        DueDateInPastError: If the provided due_datetime is in the past.
        ScheduledDateInPastError: If the provided scheduled_date is in the past.
    """

    task = get_task_for_user(user=user, task_id=task_id)
    label_pks: list[int] | None = None
    if labels is not None:
        label_pks = _validated_label_pks(labels=labels, owner=user)

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
        # ``auto_now`` is only applied to the fields Django saves, so the
        # timestamp must be named explicitly.
        fields_to_update.append("modified_at")
        task.save(update_fields=fields_to_update)
        updated = True

    if label_pks is not None:
        current_label_ids = set(task.labels.values_list("pk", flat=True))
        if set(label_pks) != current_label_ids:
            task.labels.set(label_pks)
            if not fields_to_update:
                # An m2m write does not touch the task row; stamp it so "last
                # modified" and modified_at sorting stay accurate.
                task.save(update_fields=["modified_at"])
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
