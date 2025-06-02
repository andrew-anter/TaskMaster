from datetime import date, datetime
from .models import Task
from django.db import transaction
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
    # TODO: check for dates that they are in the future
    # TODO: if an optional value is not sent, then do not create the object with it

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
