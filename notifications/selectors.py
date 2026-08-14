from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Notification

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from accounts.models import User


def get_notifications_for_user(
    *, user: User, limit: int | None = None, is_read: bool | None = None
) -> QuerySet[Notification]:
    """
    Return notifications addressed to ``user``, newest first.

    ``is_read`` optionally filters to read/unread notifications. ``limit``
    caps the number of rows returned.
    """
    queryset = Notification.objects.filter(recipient=user)
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    if limit is not None:
        queryset = queryset[:limit]
    return queryset


def get_unread_notifications_count(*, user: User) -> int:
    """Return the number of unread notifications for ``user``."""
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_notification_for_user(*, user: User, notification_id: int) -> Notification:
    """
    Fetch a single notification, ensuring it belongs to ``user``.

    Raises:
        Notification.DoesNotExist: if the notification does not exist or is
            addressed to a different user.
    """
    return Notification.objects.get(pk=notification_id, recipient=user)
