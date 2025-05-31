from datetime import date, datetime
from .models import TodoItem
from django.db import transaction


@transaction.atomic
def add_todo_service(
    *,
    title: str,
    description: str | None,
    status: str,
    priority: int,
    due_date: datetime | None,
    scheduled_date: date | None,
) -> TodoItem:
    # TODO: Add validation checks
    # TODO: check for dates that they are in the future
    # TODO: if an optional value is not sent, then do not create the object with it

    todo_item = TodoItem.objects.create(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        scheduled_date=scheduled_date,
    )
    return todo_item
