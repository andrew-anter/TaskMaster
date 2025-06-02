from django.utils import timezone
from django.db.models import QuerySet
from .models import Task
from django.db.models import Q
from django.contrib.auth.models import User


def get_all_tasks(*, user: User) -> QuerySet[Task]:
    return Task.objects.filter(owner=user)


def get_upcoming_tasks(*, user: User) -> QuerySet[Task]:
    tasks = get_all_tasks(user=user)
    return tasks.filter(due_date__isnull=False).order_by("due_date")[:5]


def get_today_tasks(*, user: User) -> QuerySet[Task]:
    tasks = get_all_tasks(user=user)
    today = timezone.now().date()
    return tasks.filter(
        Q(due_date__date=today) | Q(scheduled_date=today) | Q(created_at__date=today)
    )
