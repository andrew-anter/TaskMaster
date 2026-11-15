from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import Notification
from .services import invalidate_unread_count_on_commit

# Bounds both the instantiated rows per DELETE and the SQL parameter count.
CLEANUP_CHUNK_SIZE = 5000


def _raw_delete(queryset: QuerySet[Notification]) -> int:
    """Delete the queryset's rows in one statement, without firing signals."""
    return queryset._raw_delete(using=queryset.db)  # type: ignore[attr-defined]


@shared_task
def cleanup_old_notifications() -> int:
    """
    Delete notifications past their retention windows.

    Read notifications (those with a ``read_at`` timestamp) are removed
    ``NOTIFICATIONS_READ_RETENTION_DAYS`` after they were read; unread ones
    (``read_at`` is ``NULL``) are removed after
    ``NOTIFICATIONS_UNREAD_RETENTION_DAYS`` so the table cannot grow without
    bound for users who never clear their inbox. Returns the number of rows
    deleted.

    Expired rows are removed in pk chunks with ``_raw_delete``, which skips
    row signals: a plain queryset ``delete()`` would instantiate every expired
    row and fire one cache DELETE per row through the ``post_delete``
    receiver. The unread-count cache is dropped explicitly instead, once per
    affected recipient, after the surrounding transaction commits.
    """
    now = timezone.now()

    read_cutoff = now - timedelta(days=settings.NOTIFICATIONS_READ_RETENTION_DAYS)
    unread_cutoff = now - timedelta(days=settings.NOTIFICATIONS_UNREAD_RETENTION_DAYS)
    expired_querysets = [
        Notification.objects.filter(read_at__lt=read_cutoff),
        Notification.objects.filter(read_at__isnull=True, created_at__lt=unread_cutoff),
    ]

    deleted = 0
    affected_recipients: set[int] = set()
    with transaction.atomic():
        for queryset in expired_querysets:
            ids = list(queryset.values_list("pk", flat=True))
            if not ids:
                continue
            affected_recipients.update(
                queryset.values_list("recipient_id", flat=True).distinct()
            )
            for start in range(0, len(ids), CLEANUP_CHUNK_SIZE):
                chunk = Notification.objects.filter(
                    pk__in=ids[start : start + CLEANUP_CHUNK_SIZE]
                )
                deleted += _raw_delete(chunk)

        for recipient_id in affected_recipients:
            invalidate_unread_count_on_commit(user_id=recipient_id)

    return deleted