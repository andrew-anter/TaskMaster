import pytest

from accounts.models import User
from tasks.services import task_add_service

from ..selectors import LabelSelector
from ..services import LabelService


@pytest.fixture
def user():
    """Creates and returns a standard user instance."""
    return User.objects.create_user(username="testuser")


@pytest.fixture
def label_selector(user):
    """Creates an instance of LabelSelector using the user fixture."""
    return LabelSelector(user=user)


@pytest.fixture
def label_service(user):
    return LabelService(user=user)


@pytest.fixture
def labels(label_service):
    label_data = [
        {"name": "Urgent", "color": "#EF4444"},
        {"name": "Backend", "color": "#3B82F6"},
    ]
    return [label_service.create_label(**data) for data in label_data]


@pytest.fixture
def task(user):
    return task_add_service(
        title="test title",
        description="test description",
        owner=user,
    )
