from django.utils import timezone
from django.db.models import QuerySet
from .models import Task
from django.db.models import Q


def get_all_tasks() -> QuerySet[Task]:
    return Task.objects.all()


def get_upcoming_tasks() -> QuerySet[Task]:
    tasks = get_all_tasks()
    return tasks.filter(due_date__isnull=False).order_by("due_date")[:5]


def get_today_tasks() -> QuerySet[Task]:
    tasks = get_all_tasks()
    today = timezone.now().date()
    return tasks.filter(
        Q(due_date__date=today) | Q(scheduled_date=today) | Q(created_at__date=today)
    )
