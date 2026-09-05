import pytest
from django.urls import reverse

from accounts.models import User
from tasks.models import Task
from tasks.services import task_add_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_logged_in(client, owner):
    client.force_login(owner)
    return client


@pytest.fixture
def sample_task(owner):
    return task_add_service(
        title="Sample task",
        description="A sample description",
        status=Task.Status.TODO,
        priority=Task.Priority.MEDIUM,
        owner=owner,
    )


class TestTaskAddView:
    def test_get_renders_form(self, client_logged_in):
        response = client_logged_in.get(reverse("task_add"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_creates_task(self, client_logged_in, owner):
        data = {
            "title": "New task",
            "description": "New description",
            "status": Task.Status.TODO,
            "priority": Task.Priority.HIGH,
        }
        response = client_logged_in.post(reverse("task_add"), data)
        assert response.status_code in (200, 302)
        assert Task.objects.filter(owner=owner, title="New task").exists()

    def test_post_without_description(self, client_logged_in, owner):
        data = {
            "title": "No desc task",
            "status": Task.Status.TODO,
            "priority": Task.Priority.LOW,
        }
        response = client_logged_in.post(reverse("task_add"), data)
        assert response.status_code in (200, 302)
        assert Task.objects.filter(owner=owner, title="No desc task").exists()

    def test_post_invalid_form_returns_errors(self, client_logged_in):
        data = {
            "title": "",
            "status": Task.Status.TODO,
            "priority": Task.Priority.MEDIUM,
        }
        response = client_logged_in.post(reverse("task_add"), data)
        assert response.status_code == 200
        assert response.context["form"].errors

    def test_htmx_post_returns_partial(self, client_logged_in):
        data = {
            "title": "HTMX task",
            "status": Task.Status.TODO,
            "priority": Task.Priority.LOW,
        }
        response = client_logged_in.post(
            reverse("task_add"), data, HTTP_HX_REQUEST="true"
        )
        assert response.status_code in (200, 302)


class TestTaskDetailView:
    def test_get_renders_task(self, client_logged_in, sample_task):
        response = client_logged_in.get(reverse("task_detail", args=[sample_task.pk]))
        assert response.status_code == 200
        assert response.context["task"] == sample_task

    def test_get_nonexistent_returns_404(self, client_logged_in):
        response = client_logged_in.get(reverse("task_detail", args=[9999]))
        assert response.status_code == 404

    def test_post_updates_task(self, client_logged_in, sample_task):
        data = {
            "title": "Updated title",
            "description": "Updated description",
            "status": Task.Status.IN_PROGRESS,
            "priority": Task.Priority.HIGH,
        }
        response = client_logged_in.post(
            reverse("task_detail", args=[sample_task.pk]), data
        )
        assert response.status_code in (200, 302)
        sample_task.refresh_from_db()
        assert sample_task.title == "Updated title"

    def test_get_edit_mode(self, client_logged_in, sample_task):
        response = client_logged_in.get(
            reverse("task_detail", args=[sample_task.pk]) + "?mode=edit"
        )
        assert response.status_code == 200
        assert response.context["editing"] is True


class TestTaskUpdateView:
    def test_get_renders_form(self, client_logged_in, sample_task):
        response = client_logged_in.get(reverse("task_update", args=[sample_task.pk]))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_updates_task(self, client_logged_in, sample_task):
        data = {
            "title": "Updated via update view",
            "description": "Updated desc",
            "status": Task.Status.ON_HOLD,
            "priority": Task.Priority.LOW,
        }
        response = client_logged_in.post(
            reverse("task_update", args=[sample_task.pk]), data
        )
        assert response.status_code in (200, 302)
        sample_task.refresh_from_db()
        assert sample_task.title == "Updated via update view"

    def test_post_invalid_form_returns_errors(self, client_logged_in, sample_task):
        data = {
            "title": "",
            "status": Task.Status.TODO,
            "priority": Task.Priority.MEDIUM,
        }
        response = client_logged_in.post(
            reverse("task_update", args=[sample_task.pk]), data
        )
        assert response.status_code == 200
        assert response.context["form"].errors


class TestTaskStatusToggleView:
    def test_post_toggles_todo_to_completed(self, client_logged_in, sample_task):
        assert sample_task.status == Task.Status.TODO
        response = client_logged_in.post(
            reverse("update_task_status", args=[sample_task.pk]),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        sample_task.refresh_from_db()
        assert sample_task.status == Task.Status.COMPLETED

    def test_post_toggles_completed_to_todo(self, client_logged_in, owner):
        task = task_add_service(
            title="Done task",
            description="",
            status=Task.Status.COMPLETED,
            priority=Task.Priority.MEDIUM,
            owner=owner,
        )
        response = client_logged_in.post(
            reverse("update_task_status", args=[task.pk]),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        task.refresh_from_db()
        assert task.status == Task.Status.TODO


class TestTaskDeleteView:
    def test_post_deletes_task(self, client_logged_in, sample_task):
        task_id = sample_task.pk
        response = client_logged_in.post(reverse("task_delete", args=[task_id]))
        assert response.status_code == 200
        assert not Task.objects.filter(pk=task_id).exists()


class TestAllTasksView:
    def test_get_renders(self, client_logged_in, sample_task):
        response = client_logged_in.get(reverse("all_tasks"))
        assert response.status_code == 200
        assert "all_tasks" in response.context

    def test_filter_by_status(self, client_logged_in, owner):
        task_add_service(
            title="Done",
            description="",
            status=Task.Status.COMPLETED,
            priority=Task.Priority.LOW,
            owner=owner,
        )
        response = client_logged_in.get(reverse("all_tasks") + "?status=COMPLETED")
        assert response.status_code == 200
        tasks = response.context["all_tasks"]
        assert all(t.status == Task.Status.COMPLETED for t in tasks)


class TestTaskListView:
    def test_get_renders(self, client_logged_in, sample_task):
        response = client_logged_in.get(reverse("home"))
        assert response.status_code == 200
        assert "today_tasks" in response.context


class TestTaskListByLabelView:
    def test_get_renders(self, client_logged_in, owner):
        from labels.models import Label

        label = Label.objects.create(name="TestLabel", color="#000000", owner=owner)
        task_add_service(
            title="Labeled task",
            description="",
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            owner=owner,
            labels=[label.pk],
        )
        response = client_logged_in.get(reverse("tasks_by_label", args=[label.pk]))
        assert response.status_code == 200

    def test_other_user_label_returns_404(self, client_logged_in, owner):
        from labels.models import Label

        other_user = User.objects.create_user(username="other", password="pass1234")
        label = Label.objects.create(name="Private", color="#000000", owner=other_user)
        response = client_logged_in.get(reverse("tasks_by_label", args=[label.pk]))
        assert response.status_code == 404
