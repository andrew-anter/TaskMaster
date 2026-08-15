import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from tasks.models import Task

from ..models import Notification
from ..services import (
    mark_all_notifications_read,
    mark_notification_read,
    notify,
    notify_bulk,
    notify_many,
)


@pytest.mark.django_db
class TestNotify:
    def test_creates_notification_with_defaults(self, user):
        notification = notify(recipient=user, type="test", message="Hello")

        assert notification is not None
        assert Notification.objects.filter(pk=notification.pk).exists()
        assert notification.recipient == user
        assert notification.type == "test"
        assert notification.message == "Hello"
        assert notification.link == ""
        assert notification.read_at is None
        assert notification.actor is None
        assert notification.target is None

    def test_stores_link_and_actor(self, user, other_user):
        notification = notify(
            recipient=user,
            type="test",
            message="x",
            link="/tasks/update/1/",
            actor=other_user,
        )
        assert notification is not None
        assert notification.link == "/tasks/update/1/"
        assert notification.actor == other_user

    def test_resolves_generic_target(self, user, task):
        notification = notify(recipient=user, type="test", message="x", target=task)
        assert notification is not None
        assert notification.target == task
        assert notification.target_content_type == ContentType.objects.get_for_model(
            Task
        )
        assert notification.target_object_id == task.pk

    def test_dedupe_key_is_idempotent(self, user):
        first = notify(recipient=user, type="test", message="x", dedupe_key="key-1")
        second = notify(recipient=user, type="test", message="x", dedupe_key="key-1")

        assert first is not None
        assert second is None
        assert (
            Notification.objects.filter(recipient=user, dedupe_key="key-1").count() == 1
        )

    def test_different_dedupe_keys_create_separate_notifications(self, user):
        notify(recipient=user, type="test", message="x", dedupe_key="key-1")
        notification = notify(
            recipient=user, type="test", message="x", dedupe_key="key-2"
        )

        assert notification is not None
        assert Notification.objects.filter(recipient=user).count() == 2

    def test_dedupe_key_is_per_recipient(self, user, other_user):
        notify(recipient=user, type="test", message="x", dedupe_key="shared")
        notification = notify(
            recipient=other_user, type="test", message="y", dedupe_key="shared"
        )

        assert notification is not None
        assert Notification.objects.filter(recipient=other_user).count() == 1


@pytest.mark.django_db
class TestNotifyBulk:
    def test_creates_for_each_recipient(self, user, other_user):
        created = notify_bulk(recipients=[user, other_user], type="test", message="x")

        assert created == 2
        assert Notification.objects.filter(recipient=user).count() == 1
        assert Notification.objects.filter(recipient=other_user).count() == 1

    def test_accepts_a_queryset(self, user, other_user):
        from accounts.models import User

        created = notify_bulk(
            recipients=User.objects.filter(username__in=["notif-user", "other-user"]),
            type="test",
            message="x",
        )
        assert created == 2

    def test_skips_recipients_with_existing_dedupe_keys(self, user, other_user):
        notify(recipient=user, type="test", message="x", dedupe_key="a")

        created = notify_bulk(
            recipients=[user, other_user],
            type="test",
            message="x",
            dedupe_keys=["a", "b"],
        )

        assert created == 1
        assert Notification.objects.filter(recipient=user).count() == 1
        assert Notification.objects.filter(recipient=other_user).count() == 1

    def test_empty_recipients_returns_zero(self):
        assert notify_bulk(recipients=[], type="test", message="x") == 0

    def test_mismatched_dedupe_keys_raise(self, user):
        with pytest.raises(ValueError):
            notify_bulk(
                recipients=[user],
                type="test",
                message="x",
                dedupe_keys=["a", "b"],
            )


@pytest.mark.django_db
class TestNotifyMany:
    def test_creates_heterogeneous_entries(self, user, other_user):
        created = notify_many(
            entries=[
                {"recipient": user, "type": "a", "message": "x"},
                {"recipient": other_user, "type": "b", "message": "y"},
            ]
        )

        assert created == 2
        assert Notification.objects.filter(recipient=user, type="a").exists()
        assert Notification.objects.filter(recipient=other_user, type="b").exists()

    def test_empty_entries(self):
        assert notify_many(entries=[]) == 0

    def test_unknown_entry_key_raises(self, user):
        with pytest.raises(ValueError):
            notify_many(
                entries=[{"recipient": user, "type": "a", "message": "x", "bogus": 1}]
            )

    def test_missing_required_key_raises(self, user):
        with pytest.raises(ValueError):
            notify_many(entries=[{"recipient": user, "type": "a"}])

    def test_validation_runs_before_any_insert(self, user):
        with pytest.raises(ValueError):
            notify_many(
                entries=[
                    {"recipient": user, "type": "a", "message": "x", "bogus": 1},
                    {"recipient": user, "type": "b", "message": "y"},
                ]
            )
        assert Notification.objects.count() == 0

    def test_skips_existing_dedupe_keys(self, user, other_user):
        notify(recipient=user, type="a", message="x", dedupe_key="k1")

        created = notify_many(
            entries=[
                {"recipient": user, "type": "a", "message": "x", "dedupe_key": "k1"},
                {
                    "recipient": other_user,
                    "type": "a",
                    "message": "x",
                    "dedupe_key": "k2",
                },
            ]
        )

        assert created == 1
        assert Notification.objects.filter(recipient=other_user).count() == 1

    def test_resolves_target(self, user, task):
        created = notify_many(
            entries=[
                {
                    "recipient": user,
                    "type": "a",
                    "message": "x",
                    "target": task,
                }
            ]
        )
        assert created == 1
        notification = Notification.objects.get(recipient=user)
        assert notification.target == task
        assert notification.target_content_type == ContentType.objects.get_for_model(
            Task
        )
        assert notification.target_object_id == task.pk


@pytest.mark.django_db
class TestNotificationConstraint:
    def test_duplicate_dedupe_key_raises_integrity_error(self, user):
        Notification.objects.create(
            recipient=user, type="a", message="x", dedupe_key="same"
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Notification.objects.create(
                    recipient=user, type="a", message="y", dedupe_key="same"
                )

    def test_empty_dedupe_keys_are_not_constrained(self, user):
        Notification.objects.create(recipient=user, type="a", message="x")
        Notification.objects.create(recipient=user, type="a", message="y")
        assert Notification.objects.filter(recipient=user).count() == 2


@pytest.mark.django_db
class TestMarkRead:
    def test_mark_notification_read(self, user, notification):
        marked = mark_notification_read(recipient=user, notification_id=notification.pk)

        assert marked.read_at is not None

    def test_mark_notification_read_is_owner_only(self, other_user, notification):
        with pytest.raises(Notification.DoesNotExist):
            mark_notification_read(
                recipient=other_user, notification_id=notification.pk
            )

    def test_mark_all_read(self, user):
        notify(recipient=user, type="a", message="x")
        notify(recipient=user, type="b", message="y")

        updated = mark_all_notifications_read(recipient=user)

        assert updated == 2
        assert (
            Notification.objects.filter(recipient=user, read_at__isnull=True).count()
            == 0
        )
        assert (
            Notification.objects.filter(recipient=user, read_at__isnull=False).count()
            == 2
        )

    def test_mark_all_read_ignores_other_users(self, user, other_user, notification):
        mark_all_notifications_read(recipient=other_user)

        notification.refresh_from_db()
        assert notification.read_at is None


@pytest.mark.django_db
class TestCascadeDeleteOnTargetDelete:
    def test_deleting_target_deletes_its_notifications(self, user, task):
        notification = notify(recipient=user, type="reminder", message="x", target=task)
        assert notification is not None

        task.delete()

        assert not Notification.objects.filter(pk=notification.pk).exists()

    def test_delete_service_cascades_to_notifications(self, user, task):
        from tasks.services import task_delete_service

        notification = notify(recipient=user, type="reminder", message="x", target=task)
        assert notification is not None

        task_delete_service(user=user, task_id=task.pk)

        assert not Notification.objects.filter(pk=notification.pk).exists()

    def test_deleting_other_instances_keeps_notifications(self, user, task):
        other = Task.objects.create(owner=user, title="unrelated")
        notification = notify(recipient=user, type="reminder", message="x", target=task)
        assert notification is not None

        other.delete()

        assert Notification.objects.filter(pk=notification.pk).exists()
