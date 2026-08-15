import pytest

from ..models import Notification
from ..selectors import (
    get_notification_for_user,
    get_notifications_for_user,
    get_unread_notifications_count,
)
from ..services import mark_all_notifications_read, notify


@pytest.mark.django_db
class TestNotificationSelectors:
    def test_returns_only_own_notifications(self, user, other_user, notification):
        assert list(get_notifications_for_user(user=user)) == [notification]
        assert get_notifications_for_user(user=other_user).count() == 0

    def test_orders_newest_first(self, user):
        first = notify(recipient=user, type="t", message="first")
        second = notify(recipient=user, type="t", message="second")

        assert list(get_notifications_for_user(user=user)) == [second, first]

    def test_limit(self, user):
        for index in range(5):
            notify(recipient=user, type="t", message=f"m{index}")

        assert get_notifications_for_user(user=user, limit=2).count() == 2

    def test_is_read_filter(self, user, notification):
        assert get_notifications_for_user(user=user, is_read=False).count() == 1
        assert get_notifications_for_user(user=user, is_read=True).count() == 0

    def test_unread_count(self, user):
        assert get_unread_notifications_count(user=user) == 0
        notify(recipient=user, type="t", message="x")
        notify(recipient=user, type="t", message="y")
        assert get_unread_notifications_count(user=user) == 2

    def test_unread_count_cache_tracks_writes(self, user):
        # Warm the cache, then verify writes invalidate it immediately.
        assert get_unread_notifications_count(user=user) == 0
        notify(recipient=user, type="t", message="x")
        assert get_unread_notifications_count(user=user) == 1
        mark_all_notifications_read(recipient=user)
        assert get_unread_notifications_count(user=user) == 0

    def test_get_notification_for_user(self, user, notification):
        fetched = get_notification_for_user(user=user, notification_id=notification.pk)
        assert fetched == notification

    def test_get_notification_is_owner_only(self, other_user, notification):
        with pytest.raises(Notification.DoesNotExist):
            get_notification_for_user(user=other_user, notification_id=notification.pk)
