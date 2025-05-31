from django.db.models import QuerySet
from .models import TodoItem


def get_todo_items() -> QuerySet[TodoItem]:
    return TodoItem.objects.all()


def get_upcoming_tasks() -> QuerySet[TodoItem]:
    return TodoItem.objects.filter(due_date__isnull=False).order_by("due_date")[:5]
