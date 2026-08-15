import pytest
from django.utils import timezone

from accounts.models import User
from ..models import Task
from ..services import task_add_service


@pytest.fixture
def owner() -> User:
    """Fixture to provide a user object for tests."""
    user, _ = User.objects.get_or_create(username="testuser")
    return user


@pytest.fixture
def valid_task_data(owner: User) -> dict:
    """Fixture to provide a dictionary of valid data for creating a task."""
    return {
        "title": "Test title",
        "description": "Test Description",
        "status": Task.Status.IN_PROGRESS,
        "priority": Task.Priority.MEDIUM,
        "due_datetime": timezone.now(),
        "scheduled_date": timezone.now().date(),
        "owner": owner,
    }


@pytest.fixture
def task_for_testing(valid_task_data: dict) -> Task:
    """
    This fixture now DEPENDS on the 'valid_task_data' fixture.
    Pytest will run 'valid_task_data' first and pass its result in.
    """
    task = task_add_service(**valid_task_data)
    return task


@pytest.fixture
def todo_task(valid_task_data) -> Task:
    """Fixture to provide a task with a 'TODO' status."""

    updated_data = {**valid_task_data, "status": Task.Status.TODO}
    return task_add_service(**updated_data)


@pytest.fixture
def completed_task(valid_task_data) -> Task:
    """Fixture to provide a task with a 'COMPLETED' status."""
    updated_data = {**valid_task_data, "status": Task.Status.COMPLETED}
    return task_add_service(**updated_data)


@pytest.fixture
def in_progress_task(valid_task_data) -> Task:
    """Fixture to provide a task with an 'IN_PROGRESS' status."""
    updated_data = {**valid_task_data, "status": Task.Status.IN_PROGRESS}
    return task_add_service(**updated_data)


@pytest.fixture
def on_hold_task(valid_task_data) -> Task:
    """Fixture to provide a task with an 'ON_HOLD' status."""
    updated_data = {**valid_task_data, "status": Task.Status.ON_HOLD}
    return task_add_service(**updated_data)
