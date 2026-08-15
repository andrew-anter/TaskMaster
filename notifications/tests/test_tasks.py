from datetime import timedelta

import pytest
from django.utils import timezone

from ..models import Notification
from ..services import mark_notification_read, notify
from ..tasks import cleanup_old_notifications


@pytest.mark.django_db
class TestCleanupOldNotifications:
    def test_deletes_expired_read_notifications(self, user):
        notification = notify(recipient=user, type="a", message="x")
        assert notification is not None
        mark_notification_read(recipient=user, notification_id=notification.pk)
        Notification.objects.filter(pk=notification.pk).update(
            read_at=timezone.now() - timedelta(days=31)
        )

        deleted = cleanup_old_notifications()

        assert deleted == 1
        assert not Notification.objects.filter(pk=notification.pk).exists()

    def test_keeps_recently_read_notifications(self, user):
        notification = notify(recipient=user, type="a", message="x")
        assert notification is not None
        mark_notification_read(recipient=user, notification_id=notification.pk)
        Notification.objects.filter(pk=notification.pk).update(
            read_at=timezone.now() - timedelta(days=10)
        )

        deleted = cleanup_old_notifications()

        assert deleted == 0
        assert Notification.objects.filter(pk=notification.pk).exists()

    def test_deletes_expired_unread_notifications(self, user):
        notification = notify(recipient=user, type="a", message="x")
        assert notification is not None
        Notification.objects.filter(pk=notification.pk).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        deleted = cleanup_old_notifications()

        assert deleted == 1
        assert not Notification.objects.filter(pk=notification.pk).exists()

    def test_keeps_recent_unread_notifications(self, user):
        notification = notify(recipient=user, type="a", message="x")
        assert notification is not None

        deleted = cleanup_old_notifications()

        assert deleted == 0
        assert Notification.objects.filter(pk=notification.pk).exists()

    def test_unread_notifications_never_read_use_created_at(self, user):
        # Unread rows have read_at NULL; they expire based on creation time.
        notification = notify(recipient=user, type="a", message="x")
        assert notification is not None
        Notification.objects.filter(pk=notification.pk).update(
            read_at=None,
            created_at=timezone.now() - timedelta(days=91),
        )

        deleted = cleanup_old_notifications()

        assert deleted == 1
        assert not Notification.objects.filter(pk=notification.pk).exists()
