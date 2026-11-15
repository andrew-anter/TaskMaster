from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from labels.models import Label
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
def other_user():
    return User.objects.create_user(username="intruder", password="testpass1234")


@pytest.fixture
def foreign_label(other_user):
    return Label.objects.create(name="Theirs", color="#333333", owner=other_user)


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
        assert response.data["count"] == 1
        assert [task["id"] for task in response.data["results"]] == [sample_task.pk]

    def test_list_tasks_is_paginated(self, auth_client, owner):
        Task.objects.bulk_create(
            [Task(owner=owner, title=f"Bulk {i}") for i in range(55)]
        )

        response = auth_client.get(reverse("list-tasks-api"))

        assert response.status_code == 200
        assert response.data["count"] == 55
        assert len(response.data["results"]) == 50
        assert response.data["next"] is not None

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

    def test_create_returns_the_created_task(self, auth_client, owner):
        response = auth_client.post(
            reverse("list-tasks-api"), {"title": "With body"}, format="json"
        )

        assert response.status_code == 201
        assert response.data["title"] == "With body"
        assert response.data["status"] == Task.Status.TODO
        assert Task.objects.filter(pk=response.data["id"], owner=owner).exists()

    def test_create_with_past_due_date_returns_400(self, auth_client, owner):
        past = timezone.now() - timedelta(days=1)

        response = auth_client.post(
            reverse("list-tasks-api"),
            {"title": "Too late", "due_datetime": past.isoformat()},
            format="json",
        )

        assert response.status_code == 400
        assert "error" in response.data
        assert not Task.objects.filter(owner=owner, title="Too late").exists()

    def test_create_with_past_scheduled_date_returns_400(self, auth_client, owner):
        past = timezone.localdate() - timedelta(days=1)

        response = auth_client.post(
            reverse("list-tasks-api"),
            {"title": "Too late", "scheduled_date": past.isoformat()},
            format="json",
        )

        assert response.status_code == 400
        assert not Task.objects.filter(owner=owner, title="Too late").exists()

    def test_create_with_foreign_label_returns_400(
        self, auth_client, owner, foreign_label
    ):
        response = auth_client.post(
            reverse("list-tasks-api"),
            {"title": "Sneaky", "labels": [foreign_label.pk]},
            format="json",
        )

        assert response.status_code == 400
        assert "error" in response.data
        assert not Task.objects.filter(owner=owner, title="Sneaky").exists()

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

    def test_patch_with_foreign_label_returns_400(
        self, auth_client, sample_task, foreign_label
    ):
        response = auth_client.patch(
            reverse("task-detail-api", args=[sample_task.pk]),
            {"labels": [foreign_label.pk]},
            format="json",
        )

        assert response.status_code == 400
        assert "error" in response.data
        sample_task.refresh_from_db()
        assert sample_task.labels.count() == 0

    def test_patch_without_changes_returns_bodyless_304(self, auth_client, sample_task):
        response = auth_client.patch(
            reverse("task-detail-api", args=[sample_task.pk]),
            {"title": sample_task.title},
            format="json",
        )

        assert response.status_code == 304
        assert response.content == b""

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
