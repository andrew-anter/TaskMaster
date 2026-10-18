from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db.models import Case, F, Q, QuerySet, Value, When
from django.utils import timezone

from .models import Task

User = settings.AUTH_USER_MODEL

SORTABLE_FIELDS = frozenset(
    {
        "title",
        "status",
        "priority",
        "due_datetime",
        "scheduled_date",
        "created_at",
        "modified_at",
    }
)

OVERDUE_TASKS_LIMIT = 50


def get_task_for_user(*, user: User, task_id: int) -> Task:
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


def get_all_tasks_for_user(*, user: User) -> QuerySet[Task]:
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


UPCOMING_TASKS_LIMIT = 5


def default_task_order() -> list:
    """
    Sensible "no sort selected" ordering for task lists.

    Open tasks come before completed ones, then the soonest due date (tasks
    without a due date last), then highest priority first. ``Meta.ordering``
    stays untouched: it is part of the API contract.
    """
    completed_last = Case(
        When(status=Task.Status.COMPLETED, then=Value(1)),
        default=Value(0),
    )
    priority_rank = Case(
        When(priority=Task.Priority.HIGH, then=Value(1)),
        When(priority=Task.Priority.MEDIUM, then=Value(2)),
        When(priority=Task.Priority.LOW, then=Value(3)),
        default=Value(4),
    )
    return [
        completed_last.asc(),
        F("due_datetime").asc(nulls_last=True),
        priority_rank.asc(),
    ]


def get_upcoming_tasks_for_user(*, user: User) -> QuerySet[Task]:
    """
    Retrieves the next 5 upcoming tasks for a user beyond today.

    Tasks due today (and overdue ones) belong to their own dashboard sections,
    so this queryset deliberately starts at tomorrow: the dashboard sections
    stay disjoint and no task is rendered twice. Tasks that only carry a
    ``scheduled_date`` in the future are listed after the due-dated ones, so
    they no longer disappear from the dashboard entirely.

    Args:
        user: The user whose upcoming tasks are to be retrieved.

    Returns:
        A limited and ordered QuerySet of the 5 nearest upcoming tasks.
    """
    today = timezone.localdate()
    tasks = get_all_tasks_for_user(user=user).filter(
        Q(due_datetime__date__gt=today) | Q(scheduled_date__gt=today)
    )
    return tasks.order_by(
        F("due_datetime").asc(nulls_last=True), "scheduled_date"
    )[:UPCOMING_TASKS_LIMIT]


def get_today_tasks_for_user(*, user: User) -> QuerySet[Task]:
    """
    Retrieves tasks for a user that are due or scheduled for today.

    Tasks are only included if they have an explicit due date or scheduled
    date falling on today; newly created tasks without such a date are not
    shown (they belong to "All Tasks", not today's agenda).

    Args:
        user: The user whose tasks for today are to be retrieved.

    Returns:
        A QuerySet of tasks that are due or scheduled today.
    """
    tasks = get_all_tasks_for_user(user=user)
    today = timezone.now().date()
    now = timezone.now()
    return tasks.filter(
        Q(due_datetime__date=today, due_datetime__gte=now) | Q(scheduled_date=today)
    )


def _overdue_queryset(*, user: User) -> QuerySet[Task]:
    """Overdue = incomplete tasks whose due date has passed."""
    now = timezone.now()
    return (
        get_all_tasks_for_user(user=user)
        .filter(due_datetime__isnull=False, due_datetime__lt=now)
        .exclude(status=Task.Status.COMPLETED)
    )


def get_overdue_tasks_for_user(*, user: User) -> QuerySet[Task]:
    """
    Retrieves a user's incomplete tasks whose due date is in the past.

    Completed tasks are excluded (they should not be nagged as overdue). The
    result is capped at ``OVERDUE_TASKS_LIMIT`` oldest-overdue-first so the
    dashboard stays bounded even with a large backlog. Use
    ``get_overdue_tasks_count_for_user`` for the uncapped total.

    Args:
        user: The user whose overdue tasks are to be retrieved.

    Returns:
        A limited QuerySet of overdue tasks, ordered by due date (oldest first).
    """
    return _overdue_queryset(user=user).order_by("due_datetime")[:OVERDUE_TASKS_LIMIT]


def get_overdue_tasks_count_for_user(*, user: User) -> int:
    """Total number of overdue tasks for ``user`` (ignoring the display cap)."""
    return _overdue_queryset(user=user).count()


def get_tasks_by_label(*, user: User, label_id: int) -> QuerySet[Task]:
    """
    Retrieves all tasks for a user that have a specific label, in the
    default list order (open first, then soonest due).
    """
    return (
        get_all_tasks_for_user(user=user)
        .filter(labels__id=label_id)
        .order_by(*default_task_order())
    )


def search_tasks_for_user(
    *,
    user: User,
    query: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    label_id: int | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> QuerySet[Task]:
    """
    Retrieves a user's tasks filtered by optional search criteria.

    All criteria are optional and combined with AND semantics:
    - ``query``: case-insensitive substring match on title or description.
    - ``status`` / ``priority``: exact match on the respective field.
    - ``label_id``: tasks carrying the given label.
    - ``due_from`` / ``due_to``: tasks with a due date within the range
      (inclusive, based on the date part).
    - ``sort_by``: a field from ``SORTABLE_FIELDS`` to order by; defaults to
      the model's ``Meta.ordering``.
    - ``sort_dir``: ``"asc"`` (default) or ``"desc"``.

    Args:
        user: The user whose tasks are to be retrieved.
        query: Text to match against title or description.
        status: A value from ``Task.Status``.
        priority: A value from ``Task.Priority``.
        label_id: Primary key of a label owned by the user.
        due_from: Earliest due date (inclusive).
        due_to: Latest due date (inclusive).
        sort_by: Field name to order results by.
        sort_dir: Sort direction, ``"asc"`` or ``"desc"``.

    Returns:
        A lazy QuerySet of matching tasks for the given user.
    """
    tasks = get_all_tasks_for_user(user=user)

    if query:
        tasks = tasks.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    if status:
        tasks = tasks.filter(status=status)
    if priority is not None:
        tasks = tasks.filter(priority=priority)
    if label_id is not None:
        tasks = tasks.filter(labels__id=label_id)
    if due_from:
        tasks = tasks.filter(due_datetime__date__gte=due_from)
    if due_to:
        tasks = tasks.filter(due_datetime__date__lte=due_to)

    if sort_by is None:
        tasks = tasks.order_by(*default_task_order())
    if sort_by == "priority":
        rank = Case(
            When(priority=Task.Priority.HIGH, then=Value(1)),
            When(priority=Task.Priority.MEDIUM, then=Value(2)),
            When(priority=Task.Priority.LOW, then=Value(3)),
            default=Value(4),
        )
        tasks = tasks.order_by(rank.desc() if sort_dir == "desc" else rank.asc())
    elif sort_by in SORTABLE_FIELDS:
        field = f"-{sort_by}" if sort_dir == "desc" else sort_by
        tasks = tasks.order_by(field)

    return tasks
