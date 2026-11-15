from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone

from ..models import Notification
from ..selectors import get_unread_notifications_count
from ..services import invalidate_unread_count_on_commit, mark_notification_read, notify
from ..tasks import cleanup_old_notifications

# Django ships this as a TestCase classmethod (absent from django-stubs).
capture_on_commit_callbacks = TestCase.captureOnCommitCallbacks  # type: ignore[reportAttributeAccessIssue]


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

    def test_deletes_expired_rows_in_chunks_and_sums_counts(self, user, monkeypatch):
        # A tiny chunk size crosses chunk boundaries without seeding 5000 rows.
        monkeypatch.setattr("notifications.tasks.CLEANUP_CHUNK_SIZE", 2)
        for index in range(5):
            notify(recipient=user, type="a", message=f"old {index}")
        Notification.objects.filter(recipient=user).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        with capture_on_commit_callbacks(execute=True):
            deleted = cleanup_old_notifications()

        assert deleted == 5
        assert not Notification.objects.exists()

    def test_invalidates_each_affected_recipient_exactly_once(
        self, user, other_user, monkeypatch
    ):
        invalidated: list[int] = []

        def spy(*, user_id: int) -> None:
            invalidated.append(user_id)
            invalidate_unread_count_on_commit(user_id=user_id)

        monkeypatch.setattr(
            "notifications.tasks.invalidate_unread_count_on_commit", spy
        )

        old_created = timezone.now() - timedelta(days=91)
        old_read = timezone.now() - timedelta(days=31)
        # One read-expired and one unread-expired row per recipient, so both
        # retention querysets contribute the same recipient ids.
        for recipient in (user, other_user):
            read_notification = notify(recipient=recipient, type="a", message="read")
            unread_notification = notify(
                recipient=recipient, type="a", message="unread"
            )
            assert read_notification is not None
            assert unread_notification is not None
            Notification.objects.filter(pk=read_notification.pk).update(
                read_at=old_read, created_at=old_created
            )
            Notification.objects.filter(pk=unread_notification.pk).update(
                created_at=old_created
            )
            assert get_unread_notifications_count(user=recipient) == 1

        with capture_on_commit_callbacks(execute=True):
            deleted = cleanup_old_notifications()

        assert deleted == 4
        assert sorted(invalidated) == sorted({user.pk, other_user.pk})
        # The cache really was dropped, so the badge recomputes from the DB.
        assert get_unread_notifications_count(user=user) == 0
        assert get_unread_notifications_count(user=other_user) == 0