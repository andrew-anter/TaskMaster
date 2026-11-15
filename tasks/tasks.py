from __future__ import annotations

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from notifications.services import notify_many

from .models import Task
from .reminder_types import (
    TYPE_DUE_SOON,
    TYPE_DUE_TODAY,
    TYPE_OVERDUE,
    TYPE_SCHEDULED_TODAY,
)

DUE_SOON_WINDOW = timedelta(hours=24)

logger = logging.getLogger(__name__)


def _as_aware(value) -> datetime | None:
    """Return ``value`` as a timezone-aware datetime (defensive against
    naive datetimes stored outside the services, e.g. via shell/admin)."""
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def task_reminder_specs(*, task: Task, now) -> list[tuple[str, str]]:
    """
    Compute the reminder notification specs for a single task.

    Returns a list of ``(type_key, message)`` pairs. A task never produces
    more than one due-based reminder (overdue > due today > due soon) plus an
    optional scheduled-today reminder.
    """
    due_datetime = _as_aware(task.due_datetime)
    specs: list[tuple[str, str]] = []

    if due_datetime and due_datetime < now:
        specs.append((TYPE_OVERDUE, f'Task "{task.title}" is overdue.'))
    elif due_datetime and due_datetime.date() == now.date():
        due_time = timezone.localtime(due_datetime).strftime("%H:%M")
        specs.append(
            (TYPE_DUE_TODAY, f'Task "{task.title}" is due today at {due_time}.')
        )
    elif due_datetime and due_datetime <= now + DUE_SOON_WINDOW:
        specs.append((TYPE_DUE_SOON, f'Task "{task.title}" is due within 24 hours.'))

    if task.scheduled_date and task.scheduled_date == now.date():
        specs.append(
            (
                TYPE_SCHEDULED_TODAY,
                f'Task "{task.title}" is scheduled for today.',
            )
        )

    return specs


@shared_task
def generate_reminder_notifications() -> int:
    """
    Generate reminder notifications for every user's incomplete tasks.

    Idempotent: dedupe keys (enforced unique at the database level) guarantee
    each (user, task, type) reminder is created at most once. A failure while
    handling one user is logged and skipped so every other user still gets
    their sweep; the next run regenerates the skipped reminders. Returns the
    number of reminder entries submitted (the bulk insert may drop concurrent
    duplicates).
    """
    now = timezone.now()
    submitted = 0

    for user in User.objects.exclude(is_active=False).iterator():
        try:
            tasks = Task.objects.filter(owner=user).exclude(
                status=Task.Status.COMPLETED
            )

            entries = []
            for task in tasks.iterator():
                for type_key, message in task_reminder_specs(task=task, now=now):
                    entries.append(
                        {
                            "recipient": user,
                            "type": type_key,
                            "message": message,
                            "link": reverse("task_detail", args=[task.pk]),
                            "target": task,
                            "dedupe_key": f"{type_key}:{task.pk}",
                        }
                    )

            if entries:
                submitted += notify_many(entries=entries)
        except Exception:
            # One user's write must not starve everyone after them in the sweep.
            logger.exception("Reminder sweep failed for user %s", user.pk)

    return submitted
