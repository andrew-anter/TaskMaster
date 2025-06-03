from datetime import date, datetime

from .models import Task
from django.db import transaction
from django.utils import timezone
from .exceptions import DueDateInPastError, ScheduledDateInPastError

from django.contrib.auth import get_user_model

User = get_user_model()


@transaction.atomic
def add_task_service(
    *,
    title: str,
    description: str | None,
    status: str,
    priority: int,
    due_datetime: datetime | None,
    scheduled_date: date | None,
    owner: User,
) -> Task:
    # TODO: Add validation checks

    today = timezone.now().today().date()
    if due_datetime and due_datetime.date() < today:
        raise DueDateInPastError

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
    if task.status == Task.Status.COMPLETED:
        task.status = Task.Status.TODO
    else:
        task.status = Task.Status.COMPLETED
    task.save()
    return task


@transaction.atomic
def task_update_service(
    *,
    task: Task,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    due_datetime: datetime | None = None,
    scheduled_date: date | None = None,
) -> tuple[Task, bool]:
    """
    Updates a task with the provided values.
    Only fields that are not None will be updated.

    returns: (task, updated) where updated is a flag
    that is either true when there's an update happened
    or false if there is not any updates
    """
    # A flag to check if we need to save
    fields_updated = False

    if title is not None and task.title != title:
        task.title = title
        fields_updated = True

    if description is not None and task.description != description:
        task.description = description
        fields_updated = True

    if status is not None and task.status != status:
        if status not in [choice[0] for choice in Task.Status.choices]:
            raise ValueError("Invalid status")
        task.status = status
        fields_updated = True

    if priority is not None and task.priority != priority:
        # You might want to validate if 'priority' is a valid choice from Task.Priority
        if priority not in [choice[0] for choice in Task.Priority.choices]:
            raise ValueError("Invalid priority")
        task.priority = priority
        fields_updated = True

    if due_datetime is not None:
        # Check if the provided due_datetime is in the past
        if due_datetime.tzinfo is None:
            if timezone.get_current_timezone():
                due_datetime = timezone.make_aware(
                    due_datetime, timezone.get_current_timezone()
                )

        if due_datetime < timezone.now():
            raise DueDateInPastError(
                f"The due date {due_datetime.strftime('%Y-%m-%d %H:%M')} cannot be in the past."
            )

        if task.due_datetime != due_datetime:  # Model field is task.due_date
            task.due_datetime = due_datetime
            fields_updated = True

    if scheduled_date is not None:
        if scheduled_date < timezone.now().date():
            raise ScheduledDateInPastError(
                f"The scheduled date {scheduled_date.strftime('%Y-%m-%d')} cannot be in the past."
            )
        if task.scheduled_date != scheduled_date:
            task.scheduled_date = scheduled_date
            fields_updated = True

    if fields_updated:
        task.save()
        return (task, True)

    return (task, False)
