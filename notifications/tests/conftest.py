import pytest

from accounts.models import User
from notifications.models import Notification
from notifications.services import notify


@pytest.fixture
def user(db):
    """Standard recipient user."""
    return User.objects.create_user(username="notif-user")


@pytest.fixture
def other_user(db):
    """A second user who should not see the first user's notifications."""
    return User.objects.create_user(username="other-user")


@pytest.fixture
def task(user):
    from tasks.services import task_add_service

    return task_add_service(
        title="test task",
        description="test description",
        owner=user,
    )


@pytest.fixture
def notification(user) -> Notification:
    created = notify(
        recipient=user,
        type="test_type",
        message="Test message",
        link="/tasks/update/1/",
    )
    assert created is not None
    return created
