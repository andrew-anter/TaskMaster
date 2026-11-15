import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from labels.models import Label
from tasks.management.commands.seed_data import (
    SEED_LABEL_PREFIX,
    SEED_USERNAME_PREFIX,
)
from tasks.models import Task

pytestmark = pytest.mark.django_db

SMALL_SEED = {"users": 3, "labels": 2, "tasks": 3, "batch_size": 2, "seed": 7}


def seed(**overrides):
    """Run the command with small deterministic defaults."""
    call_command("seed_data", no_notifications=True, **{**SMALL_SEED, **overrides})


def seeded_users_count() -> int:
    return User.objects.filter(username__startswith=SEED_USERNAME_PREFIX).count()


def seeded_labels_count() -> int:
    return Label.objects.filter(name__startswith=SEED_LABEL_PREFIX).count()


class TestSeedIdempotency:
    def test_rerun_does_not_grow_users_or_labels(self):
        seed()
        seed()

        assert seeded_users_count() == 3
        assert seeded_labels_count() == 2

    def test_rerun_tops_up_when_more_users_are_requested(self):
        seed(users=2, labels=1, tasks=0)
        seed(users=3, labels=2, tasks=0)

        assert seeded_users_count() == 3
        assert seeded_labels_count() == 2


class TestSeedValidation:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"users": 0},
            {"labels": -1},
            {"tasks": -1},
            {"batch_size": 0},
        ],
    )
    def test_invalid_options_raise_command_error(self, overrides):
        with pytest.raises(CommandError):
            seed(**overrides)

    def test_rejected_run_creates_nothing(self):
        with pytest.raises(CommandError):
            seed(users=0)

        assert seeded_users_count() == 0
        assert Task.objects.count() == 0


class TestSeedFlush:
    def test_flush_replaces_the_previous_seed(self):
        seed(users=2, labels=1, tasks=3)
        seed(users=1, labels=1, tasks=1, flush=True)

        assert seeded_users_count() == 1
        assert seeded_labels_count() == 1
        assert Task.objects.count() == 1


class TestSeedPassword:
    def test_password_makes_seeded_users_loginable(self):
        seed(users=2, labels=1, tasks=0, password="demo-pass-123")

        user = User.objects.get(username=f"{SEED_USERNAME_PREFIX}1")
        assert user.check_password("demo-pass-123")

    def test_password_is_applied_to_previously_seeded_users(self):
        seed(users=2, labels=1, tasks=0)
        user = User.objects.get(username=f"{SEED_USERNAME_PREFIX}1")
        assert not user.check_password("demo-pass-123")

        seed(users=2, labels=1, tasks=0, password="demo-pass-123")

        user.refresh_from_db()
        assert user.check_password("demo-pass-123")

    def test_without_password_seeded_users_cannot_log_in(self):
        seed(users=2, labels=1, tasks=0)

        user = User.objects.get(username=f"{SEED_USERNAME_PREFIX}1")
        assert not user.check_password("demo-pass-123")
