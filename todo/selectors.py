from django.db.models import QuerySet
from .models import TodoItem


def get_todo_items() -> QuerySet[TodoItem]:
    return TodoItem.objects.all()
