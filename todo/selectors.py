from __future__ import annotations

from django.contrib.auth.models import _AnyUser
from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import Task


def get_task_for_user(*, user: _AnyUser, task_id: int) -> Task:
    """
    Fetches a single task by its ID, ensuring it belongs to the specified user.

    This function acts as a permission-checked getter. It raises an exception
    if the task does not exist or if the user is not the owner, preventing
    accidental data leakage.

    Args:
        user: The user who is expected to own the task.
        task_id: The primary key of the task to retrieve.

    Returns:
        The requested Task instance.

    Raises:
        Task.DoesNotExist: If no task is found with the given ID and owner.
    """
    return Task.objects.get(pk=task_id, owner=user)


def get_all_tasks_for_user(*, user: _AnyUser) -> QuerySet[Task]:
    """
    Retrieves all tasks owned by a specific user.

    This is the primary selector for fetching a user's entire set of tasks.
    Other selectors can build upon this to apply further filtering.

    Args:
        user: The user whose tasks are to be retrieved.

    Returns:
        A lazy Django QuerySet containing all tasks for the given user.
    """
    return Task.objects.filter(owner=user)


def get_upcoming_tasks_for_user(*, user: _AnyUser) -> QuerySet[Task]:
    """
    Retrieves the next 5 upcoming tasks for a user that have a due date.

    This is useful for a "dashboard" or "agenda" view. It filters only for
    tasks with a defined due date, orders them chronologically, and takes
    the top 5 most imminent tasks.

    Args:
        user: The user whose upcoming tasks are to be retrieved.

    Returns:
        A limited and ordered QuerySet of the 5 nearest upcoming tasks.
    """
    tasks = get_all_tasks_for_user(user=user)
    return tasks.filter(due_datetime__isnull=False).order_by("due_datetime")[:5]


def get_today_tasks_for_user(*, user: _AnyUser) -> QuerySet[Task]:
    """
    Retrieves tasks for a user that are considered relevant for today.

    A task is considered "relevant for today" if it meets any of the
    following criteria:
    1. It is due today.
    2. It is scheduled for today.
    3. It was created today.

    This uses a complex lookup with Q objects to combine these conditions
    with an OR operator.

    Args:
        user: The user whose tasks for today are to be retrieved.

    Returns:
        A QuerySet of tasks that are due, scheduled, or created today.
    """
    tasks = get_all_tasks_for_user(user=user)
    today = timezone.now().date()
    return tasks.filter(
        Q(due_datetime__date=today)
        | Q(scheduled_date=today)
        | Q(created_at__date=today)
    )
