from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from labels.models import Label
from tasks.models import Task
from tasks.selectors import search_tasks_for_user
from tasks.services import task_add_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_logged_in(client, owner):
    client.force_login(owner)
    return client


def make_task(owner, **overrides):
    data = {
        "title": "Default task",
        "description": "Default description",
        "status": Task.Status.TODO,
        "priority": Task.Priority.MEDIUM,
        "owner": owner,
    }
    data.update(overrides)
    return task_add_service(**data)


@pytest.fixture
def sample_label(owner):
    return Label.objects.create(name="Work", color="#111111", owner=owner)


@pytest.fixture
def sample_tasks(owner, sample_label):
    return {
        "grocery": make_task(
            owner,
            title="Buy groceries",
            description="Milk and bread",
        ),
        "report": make_task(
            owner,
            title="Write monthly report",
            description="Q2 numbers",
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.HIGH,
            due_datetime=timezone.now() + timedelta(days=5),
        ),
        "review": make_task(
            owner,
            title="Review PR",
            description="Groceries backlog cleanup",
            status=Task.Status.COMPLETED,
            priority=Task.Priority.LOW,
            due_datetime=timezone.now() + timedelta(days=10),
            scheduled_date=timezone.now().date() + timedelta(days=3),
        ),
        "labelled": make_task(
            owner,
            title="Plan sprint",
            description="Planning",
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.NONE,
            due_datetime=timezone.now() + timedelta(days=7),
            labels=[sample_label.pk],
        ),
    }


class TestSearchTasksSelector:
    def test_no_filters_returns_all_user_tasks(self, owner, sample_tasks):
        assert search_tasks_for_user(user=owner).count() == len(sample_tasks)

    def test_text_search_matches_title(self, owner, sample_tasks):
        result = search_tasks_for_user(user=owner, query="groceries")
        assert set(result) == {sample_tasks["grocery"], sample_tasks["review"]}

    def test_text_search_matches_description_case_insensitive(
        self, owner, sample_tasks
    ):
        result = search_tasks_for_user(user=owner, query="q2 NUMBERS")
        assert list(result) == [sample_tasks["report"]]

    def test_status_filter(self, owner, sample_tasks):
        result = search_tasks_for_user(user=owner, status=Task.Status.IN_PROGRESS.value)
        assert set(result) == {sample_tasks["report"], sample_tasks["labelled"]}

    def test_priority_filter(self, owner, sample_tasks):
        result = search_tasks_for_user(user=owner, priority=Task.Priority.HIGH.value)
        assert list(result) == [sample_tasks["report"]]

    def test_label_filter(self, owner, sample_label, sample_tasks):
        result = search_tasks_for_user(user=owner, label_id=sample_label.pk)
        assert list(result) == [sample_tasks["labelled"]]

    def test_due_date_range(self, owner, sample_tasks):
        today = timezone.now().date()
        result = search_tasks_for_user(
            user=owner,
            due_from=today + timedelta(days=4),
            due_to=today + timedelta(days=8),
        )
        assert set(result) == {sample_tasks["report"], sample_tasks["labelled"]}

    def test_combined_filters_use_and_semantics(
        self, owner, sample_label, sample_tasks
    ):
        result = search_tasks_for_user(
            user=owner, query="plan", label_id=sample_label.pk
        )
        assert list(result) == [sample_tasks["labelled"]]

    def test_never_returns_other_users_tasks(self, owner, sample_tasks):
        other = User.objects.create_user(username="intruder")
        make_task(other, title="Buy groceries for someone else")

        result = search_tasks_for_user(user=owner, query="groceries")
        assert set(result) == {sample_tasks["grocery"], sample_tasks["review"]}


ALL_TASKS_URL = reverse("all_tasks")


class TestAllTasksSearchFiltersView:
    def test_renders_filter_form(self, client_logged_in):
        response = client_logged_in.get(ALL_TASKS_URL)
        assert response.status_code == 200
        assert b'name="q"' in response.content
        assert b'name="status"' in response.content
        assert b'name="priority"' in response.content
        assert b'name="label"' in response.content
        assert b'name="due_from"' in response.content
        assert b'name="due_to"' in response.content

    def test_text_search_narrows_results(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(ALL_TASKS_URL, {"q": "report"})
        assert sample_tasks["report"].title.encode() in response.content
        assert sample_tasks["grocery"].title.encode() not in response.content

    def test_combined_filters(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(
            ALL_TASKS_URL,
            {"status": Task.Status.IN_PROGRESS, "priority": str(Task.Priority.HIGH)},
        )
        assert sample_tasks["report"].title.encode() in response.content
        assert sample_tasks["labelled"].title.encode() not in response.content

    def test_invalid_status_is_ignored(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(ALL_TASKS_URL, {"status": "BOGUS"})
        assert response.status_code == 200
        assert sample_tasks["grocery"].title.encode() in response.content

    def test_invalid_priority_is_ignored(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(ALL_TASKS_URL, {"priority": "abc"})
        assert response.status_code == 200
        assert sample_tasks["grocery"].title.encode() in response.content

    def test_other_users_label_is_ignored(
        self, client_logged_in, owner, sample_label, sample_tasks
    ):
        other = User.objects.create_user(username="other-label-owner")
        foreign_label = Label.objects.create(
            name="Foreign", color="#000000", owner=other
        )

        response = client_logged_in.get(ALL_TASKS_URL, {"label": foreign_label.pk})
        assert response.status_code == 200
        assert sample_tasks["grocery"].title.encode() in response.content

    def test_invalid_date_is_ignored(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(ALL_TASKS_URL, {"due_from": "not-a-date"})
        assert response.status_code == 200
        assert sample_tasks["grocery"].title.encode() in response.content

    def test_empty_results_message_with_filters(
        self, client_logged_in, owner, sample_tasks
    ):
        response = client_logged_in.get(ALL_TASKS_URL, {"q": "zzznomatch"})
        assert b"No tasks match your search" in response.content

    def test_empty_results_message_without_filters(self, client_logged_in):
        response = client_logged_in.get(ALL_TASKS_URL)
        assert b"No tasks have been created yet" in response.content

    def test_pagination_limits_page_size(self, client_logged_in, owner):
        for i in range(30):
            make_task(owner, title=f"Bulk task {i}")

        page_one = client_logged_in.get(ALL_TASKS_URL)
        page_two = client_logged_in.get(ALL_TASKS_URL, {"page": 2})

        assert b"Bulk task 0" in page_one.content
        assert b"Bulk task 29" not in page_one.content
        assert b"Bulk task 29" in page_two.content
        assert b"Page 2 of 2" in page_two.content

    def test_pagination_preserves_filters(self, client_logged_in, owner):
        for i in range(30):
            make_task(owner, title=f"Bulk task {i}", status=Task.Status.TODO)
        make_task(owner, title="Only one in progress", status=Task.Status.IN_PROGRESS)

        response = client_logged_in.get(
            ALL_TASKS_URL,
            {"status": Task.Status.IN_PROGRESS, "page": 2},
        )
        assert b"Only one in progress" in response.content
        assert b"Bulk task 0" not in response.content


class TestTasksByLabelView:
    def test_label_view_paginates_without_filter_form(
        self, client_logged_in, owner, sample_label
    ):
        for i in range(30):
            make_task(
                owner,
                title=f"Labelled task {i}",
                labels=[sample_label.pk],
            )

        response = client_logged_in.get(
            reverse("tasks_by_label", args=[sample_label.pk])
        )

        assert response.status_code == 200
        assert b'name="q"' not in response.content
        assert b"Labelled task 0" in response.content
        assert b"Labelled task 29" not in response.content


HOME_URL = reverse("home")


class TestHomePagination:
    def test_today_section_is_paginated(self, client_logged_in, owner):
        now = timezone.now()
        for i in range(30):
            make_task(
                owner,
                title=f"Today task {i}",
                due_datetime=now + timedelta(minutes=i),
            )

        page_one = client_logged_in.get(HOME_URL)
        page_two = client_logged_in.get(HOME_URL, {"page": 2})

        assert b"Today task 0" in page_one.content
        assert b"Today task 29" not in page_one.content
        assert b"Today task 29" in page_two.content
        assert b"Page 2 of 2" in page_two.content

    def test_upcoming_section_still_renders_top_five(self, client_logged_in, owner):
        now = timezone.now()
        for i in range(30):
            make_task(
                owner,
                title=f"Today task {i}",
                due_datetime=now + timedelta(minutes=i),
            )

        response = client_logged_in.get(HOME_URL)

        assert b"Upcoming" in response.content
        assert b"Today task 4" in response.content  # 5th earliest -> upcoming top 5
        assert (
            b"Page 1 of 2" in response.content
        )  # today section paginates independently

    def test_no_pagination_when_few_today_tasks(self, client_logged_in, owner):
        make_task(owner, title="Solo task", due_datetime=timezone.now())

        response = client_logged_in.get(HOME_URL)

        assert b"Solo task" in response.content
        assert b"Page 1 of" not in response.content
