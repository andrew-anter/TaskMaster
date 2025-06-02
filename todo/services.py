from datetime import date, datetime, tzinfo

from .models import Task
from django.db import transaction
from django.utils import timezone
from .exceptions import DueDateInPastError

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
