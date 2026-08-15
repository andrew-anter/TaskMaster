import datetime

import pytest
from django.utils import timezone

from accounts.models import User
from notifications.models import Notification

from ..models import Task
from ..reminder_types import (
    TYPE_DUE_SOON,
    TYPE_DUE_TODAY,
    TYPE_OVERDUE,
    TYPE_SCHEDULED_TODAY,
)
from ..services import task_delete_service, task_update_service
from ..tasks import generate_reminder_notifications, task_reminder_specs

FIXED_NOW = timezone.make_aware(datetime.datetime(2026, 1, 1, 12, 0, 0))


@pytest.fixture
def user(db):
    return User.objects.create_user(username="reminder-user")


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr("django.utils.timezone.now", lambda: FIXED_NOW)
    return FIXED_NOW


def make_task(user, **kwargs):
    title = kwargs.pop("title", "task")
    return Task.objects.create(owner=user, title=title, **kwargs)


@pytest.mark.django_db
class TestTaskReminderSpecs:
    def test_overdue_task(self, user):
        task = make_task(
            user, title="Over", due_datetime=FIXED_NOW - datetime.timedelta(days=1)
        )
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_OVERDUE]

    def test_due_today_task(self, user):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_DUE_TODAY]

    def test_due_soon_task(self, user):
        task = make_task(
            user, title="Soon", due_datetime=FIXED_NOW + datetime.timedelta(hours=20)
        )
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_DUE_SOON]

    def test_due_today_takes_precedence_over_due_soon(self, user):
        # 6 hours from noon is still today, so only DUE_TODAY should fire.
        task = make_task(
            user, title="Edge", due_datetime=FIXED_NOW + datetime.timedelta(hours=6)
        )
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_DUE_TODAY]

    def test_scheduled_today_task(self, user):
        task = make_task(user, title="Sched", scheduled_date=FIXED_NOW.date())
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_SCHEDULED_TODAY]

    def test_due_and_scheduled_today(self, user):
        task = make_task(
            user,
            title="Both",
            due_datetime=FIXED_NOW + datetime.timedelta(hours=3),
            scheduled_date=FIXED_NOW.date(),
        )
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [
            TYPE_DUE_TODAY,
            TYPE_SCHEDULED_TODAY,
        ]

    def test_far_future_task_has_no_reminders(self, user):
        task = make_task(
            user, title="Far", due_datetime=FIXED_NOW + datetime.timedelta(days=3)
        )
        assert task_reminder_specs(task=task, now=FIXED_NOW) == []

    @pytest.mark.filterwarnings("ignore:DateTimeField .* received a naive datetime")
    def test_naive_due_datetime_does_not_crash(self, user):
        naive = datetime.datetime(2026, 1, 1, 12, 0, 0)
        task = make_task(user, title="Naive", due_datetime=naive)
        specs = task_reminder_specs(task=task, now=FIXED_NOW)
        assert [kind for kind, _ in specs] == [TYPE_DUE_TODAY]


@pytest.mark.django_db
class TestGenerateReminderNotifications:
    def test_generates_all_kinds(self, user, frozen_now):
        make_task(
            user, title="Over", due_datetime=FIXED_NOW - datetime.timedelta(days=1)
        )
        make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        make_task(
            user, title="Soon", due_datetime=FIXED_NOW + datetime.timedelta(hours=20)
        )
        make_task(user, title="Sched", scheduled_date=FIXED_NOW.date())

        created = generate_reminder_notifications()

        assert created == 4
        kinds = set(
            Notification.objects.filter(recipient=user).values_list("type", flat=True)
        )
        assert kinds == {
            TYPE_OVERDUE,
            TYPE_DUE_TODAY,
            TYPE_DUE_SOON,
            TYPE_SCHEDULED_TODAY,
        }

    def test_skips_completed_tasks(self, user, frozen_now):
        make_task(
            user,
            title="Done",
            status=Task.Status.COMPLETED,
            due_datetime=FIXED_NOW - datetime.timedelta(days=1),
        )

        assert generate_reminder_notifications() == 0
        assert Notification.objects.filter(recipient=user).count() == 0

    def test_skips_tasks_with_no_matching_reminder(self, user, frozen_now):
        make_task(
            user, title="Far", due_datetime=FIXED_NOW + datetime.timedelta(days=3)
        )

        assert generate_reminder_notifications() == 0

    def test_is_idempotent(self, user, frozen_now):
        make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )

        assert generate_reminder_notifications() == 1
        assert generate_reminder_notifications() == 0
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_stores_link_and_target(self, user, frozen_now):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )

        generate_reminder_notifications()

        notification = Notification.objects.get(recipient=user)
        assert notification.link == f"/tasks/task/{task.pk}/"
        assert notification.target == task


@pytest.mark.django_db
class TestReminderRefreshOnUpdate:
    def test_date_change_clears_old_reminders(self, user, frozen_now):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        generate_reminder_notifications()
        assert Notification.objects.filter(recipient=user).count() == 1

        task_update_service(
            task_id=task.pk,
            user=user,
            due_datetime=FIXED_NOW + datetime.timedelta(days=10),
        )

        assert Notification.objects.filter(recipient=user).count() == 0

    def test_title_only_change_clears_stale_reminders(self, user, frozen_now):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        generate_reminder_notifications()
        assert Notification.objects.filter(recipient=user).count() == 1

        task_update_service(task_id=task.pk, user=user, title="Renamed")

        assert Notification.objects.filter(recipient=user).count() == 0

    def test_title_change_regenerates_reminder_with_new_title(self, user, frozen_now):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        generate_reminder_notifications()

        task_update_service(task_id=task.pk, user=user, title="Renamed")
        generate_reminder_notifications()

        notification = Notification.objects.get(recipient=user)
        assert 'Task "Renamed"' in notification.message

    def test_delete_task_clears_reminders(self, user, frozen_now):
        task = make_task(
            user, title="Today", due_datetime=FIXED_NOW + datetime.timedelta(hours=3)
        )
        generate_reminder_notifications()
        assert Notification.objects.filter(recipient=user).count() == 1

        task_delete_service(user=user, task_id=task.pk)

        assert Notification.objects.filter(recipient=user).count() == 0
