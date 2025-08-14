import pytest

from accounts.models import User

from ..selectors import LabelSelector
from ..services import LabelService
from tasks.services import task_add_service


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
def labels(task, label_service):
    label_data = [
        {"name": "Urgent", "color": "FF0000"},  # Red
        {"name": "Backend", "color": "0000FF"},  # Blue
    ]
    created_labels = [
        label_service.create_label_for_task(task=task, **data) for data in label_data
    ]

    return created_labels


@pytest.fixture
def task(user):
    return task_add_service(
        title="test title",
        description="test description",
        owner=user,
    )
