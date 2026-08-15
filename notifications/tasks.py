from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Notification


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
    """
    now = timezone.now()
    deleted = 0

    read_cutoff = now - timedelta(days=settings.NOTIFICATIONS_READ_RETENTION_DAYS)
    read_expired = Notification.objects.filter(read_at__lt=read_cutoff)

    unread_cutoff = now - timedelta(days=settings.NOTIFICATIONS_UNREAD_RETENTION_DAYS)
    unread_expired = Notification.objects.filter(
        read_at__isnull=True, created_at__lt=unread_cutoff
    )

    with transaction.atomic():
        deleted += read_expired.delete()[0]
        deleted += unread_expired.delete()[0]

    return deleted
