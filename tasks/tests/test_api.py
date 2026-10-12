from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from tasks.models import Task
from tasks.services import task_add_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, owner):
    api_client.force_authenticate(user=owner)
    return api_client


@pytest.fixture
def sample_task(owner):
    return task_add_service(
        title="API task",
        description="API description",
        status=Task.Status.TODO,
        priority=Task.Priority.MEDIUM,
        owner=owner,
    )


class TestListCreateApi:
    def test_list_tasks(self, auth_client, sample_task):
        response = auth_client.get(reverse("list-tasks-api"))
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_create_task(self, auth_client, owner):
        data = {
            "title": "New API task",
            "description": "New desc",
            "status": "TODO",
            "priority": 2,
        }
        response = auth_client.post(reverse("list-tasks-api"), data, format="json")
        assert response.status_code == 201
        assert Task.objects.filter(owner=owner, title="New API task").exists()

    def test_unauthenticated_list(self, api_client):
        response = api_client.get(reverse("list-tasks-api"))
        assert response.status_code in (401, 403)

    def test_create_defaults_to_todo_status(self, auth_client, owner):
        """Omitting status/description must not crash (NOT NULL) and defaults to TODO."""
        response = auth_client.post(
            reverse("list-tasks-api"), {"title": "Defaulted"}, format="json"
        )

        assert response.status_code == 201
        task = Task.objects.get(owner=owner, title="Defaulted")
        assert task.status == Task.Status.TODO
        assert task.description == ""


class TestDetailUpdateDeleteApi:
    def test_get_task(self, auth_client, sample_task):
        response = auth_client.get(reverse("task-detail-api", args=[sample_task.pk]))
        assert response.status_code == 200
        assert response.data["title"] == "API task"

    def test_patch_task(self, auth_client, sample_task):
        data = {"title": "Patched title"}
        response = auth_client.patch(
            reverse("task-detail-api", args=[sample_task.pk]),
            data,
            format="json",
        )
        assert response.status_code == 200
        sample_task.refresh_from_db()
        assert sample_task.title == "Patched title"

    def test_patch_clears_due_datetime(self, auth_client, sample_task):
        sample_task.due_datetime = timezone.now() + timedelta(days=3)
        sample_task.save(update_fields=["due_datetime"])

        response = auth_client.patch(
            reverse("task-detail-api", args=[sample_task.pk]),
            {"due_datetime": None},
            format="json",
        )

        assert response.status_code == 200
        sample_task.refresh_from_db()
        assert sample_task.due_datetime is None

    def test_patch_title_only_preserves_dates(self, auth_client, sample_task):
        """A partial PATCH that omits the date fields must not clear them."""
        sample_task.due_datetime = timezone.now() + timedelta(days=3)
        sample_task.scheduled_date = (timezone.now() + timedelta(days=3)).date()
        sample_task.save(update_fields=["due_datetime", "scheduled_date"])

        response = auth_client.patch(
            reverse("task-detail-api", args=[sample_task.pk]),
            {"title": "Only the title"},
            format="json",
        )

        assert response.status_code == 200
        sample_task.refresh_from_db()
        assert sample_task.title == "Only the title"
        assert sample_task.due_datetime is not None
        assert sample_task.scheduled_date is not None

    def test_delete_task(self, auth_client, sample_task):
        response = auth_client.delete(reverse("task-detail-api", args=[sample_task.pk]))
        assert response.status_code == 204
        assert not Task.objects.filter(pk=sample_task.pk).exists()

    def test_delete_nonexistent_returns_404(self, auth_client):
        response = auth_client.delete(reverse("task-detail-api", args=[9999]))
        assert response.status_code == 404

    def test_get_nonexistent_returns_404(self, auth_client):
        response = auth_client.get(reverse("task-detail-api", args=[9999]))
        assert response.status_code == 404


class TestToggleStatusApi:
    def test_toggle_status(self, auth_client, sample_task):
        assert sample_task.status == Task.Status.TODO
        response = auth_client.post(
            reverse("toggle-task-status-api", args=[sample_task.pk])
        )
        assert response.status_code == 200
        sample_task.refresh_from_db()
        assert sample_task.status == Task.Status.COMPLETED

    def test_toggle_nonexistent_returns_404(self, auth_client):
        response = auth_client.post(reverse("toggle-task-status-api", args=[9999]))
        assert response.status_code == 404
