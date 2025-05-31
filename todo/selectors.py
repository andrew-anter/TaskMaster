from django.db.models import QuerySet
from .models import Task


def get_todo_items() -> QuerySet[Task]:
    return Task.objects.all()


def get_upcoming_tasks() -> QuerySet[Task]:
    return Task.objects.filter(due_date__isnull=False).order_by("due_date")[:5]
