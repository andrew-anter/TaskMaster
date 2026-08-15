from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import caches

from .models import Notification

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from accounts.models import User

cache = caches["notifications"]

UNREAD_COUNT_CACHE_KEY = "notifications:unread_count:{user_id}"
UNREAD_COUNT_CACHE_TIMEOUT = 60  # seconds; matches the navbar badge poll cadence


def get_notifications_for_user(
    *, user: User, limit: int | None = None, is_read: bool | None = None
) -> QuerySet[Notification]:
    """
    Return notifications addressed to ``user``, newest first.

    ``is_read`` optionally filters to read/unread notifications (``True`` for
    read, ``False`` for unread). ``limit`` caps the number of rows returned.
    """
    queryset = Notification.objects.filter(recipient=user)
    if is_read is not None:
        queryset = queryset.filter(read_at__isnull=not is_read)
    if limit is not None:
        queryset = queryset[:limit]
    return queryset


def get_unread_notifications_count(*, user: User) -> int:
    """Return the number of unread notifications for ``user``.

    The count is cached per-user for a short window (see
    ``UNREAD_COUNT_CACHE_TIMEOUT``); the write services invalidate it on
    create/read so staleness never exceeds one poll cycle.
    """
    key = UNREAD_COUNT_CACHE_KEY.format(user_id=user.pk)
    cached = cache.get(key)
    if cached is not None:
        return cached
    count = Notification.objects.filter(recipient=user, read_at__isnull=True).count()
    cache.set(key, count, UNREAD_COUNT_CACHE_TIMEOUT)
    return count


def invalidate_unread_notifications_count(*, user_id: int) -> None:
    """Drop the cached unread count for a user (called on notification writes)."""
    cache.delete(UNREAD_COUNT_CACHE_KEY.format(user_id=user_id))


def get_notification_for_user(*, user: User, notification_id: int) -> Notification:
    """
    Fetch a single notification, ensuring it belongs to ``user``.

    Raises:
        Notification.DoesNotExist: if the notification does not exist or is
            addressed to a different user.
    """
    return Notification.objects.get(pk=notification_id, recipient=user)
