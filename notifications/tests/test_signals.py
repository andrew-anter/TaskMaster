from datetime import timedelta

import pytest
from django.utils import timezone

from ..models import Notification
from ..selectors import (
    UNREAD_COUNT_CACHE_KEY,
    cache,
    get_unread_notifications_count,
)
from ..tasks import cleanup_old_notifications


def _cache_key(user) -> str:
    return UNREAD_COUNT_CACHE_KEY.format(user_id=user.pk)


@pytest.mark.django_db
class TestNotificationSignalInvalidation:
    def test_direct_orm_create_invalidates_unread_count(self, user):
        # Warm the cached count, then bypass the services with a raw create
        # (as the Django admin would) and assert the cache is dropped.
        assert get_unread_notifications_count(user=user) == 0
        assert cache.get(_cache_key(user)) == 0

        Notification.objects.create(recipient=user, type="t", message="raw")

        assert cache.get(_cache_key(user)) is None
        assert get_unread_notifications_count(user=user) == 1

    def test_direct_orm_delete_invalidates_unread_count(self, user):
        notification = Notification.objects.create(
            recipient=user, type="t", message="raw"
        )
        assert get_unread_notifications_count(user=user) == 1
        assert cache.get(_cache_key(user)) == 1

        notification.delete()

        assert cache.get(_cache_key(user)) is None
        assert get_unread_notifications_count(user=user) == 0

    def test_cleanup_invalidates_affected_recipients(self, user):
        notification = Notification.objects.create(
            recipient=user, type="t", message="old"
        )
        Notification.objects.filter(pk=notification.pk).update(
            created_at=timezone.now() - timedelta(days=91)
        )
        assert get_unread_notifications_count(user=user) == 1
        assert cache.get(_cache_key(user)) == 1

        deleted = cleanup_old_notifications()

        assert deleted == 1
        assert cache.get(_cache_key(user)) is None
        assert get_unread_notifications_count(user=user) == 0
