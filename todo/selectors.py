from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import Task

User = get_user_model()


def get_task_for_user(*, user: User, task_id: int) -> Task | None:
    try:
        return Task.objects.get(pk=task_id, owner=user)
    except Task.DoesNotExist:
        return None


def get_all_tasks(*, user: User) -> QuerySet[Task]:
    return Task.objects.filter(owner=user)


def get_upcoming_tasks(*, user: User) -> QuerySet[Task]:
    tasks = get_all_tasks(user=user)
    return tasks.filter(due_datetime__isnull=False).order_by("due_datetime")[:5]


def get_today_tasks(*, user: User) -> QuerySet[Task]:
    tasks = get_all_tasks(user=user)
    today = timezone.now().date()
    return tasks.filter(
        Q(due_datetime__date=today)
        | Q(scheduled_date=today)
        | Q(created_at__date=today)
    )
