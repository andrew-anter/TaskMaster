from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from labels.models import Label
from tasks.models import Task
from tasks.selectors import (
    OVERDUE_TASKS_LIMIT,
    get_overdue_tasks_for_user,
    get_today_tasks_for_user,
    get_upcoming_tasks_for_user,
    search_tasks_for_user,
)
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


class TestSortTasksSelector:
    def test_sort_by_title_ascending(self, owner):
        for title in ["banana", "apple", "cherry"]:
            make_task(owner, title=title)

        result = search_tasks_for_user(user=owner, sort_by="title")
        assert [t.title for t in result] == ["apple", "banana", "cherry"]

    def test_sort_by_title_descending(self, owner):
        for title in ["banana", "apple", "cherry"]:
            make_task(owner, title=title)

        result = search_tasks_for_user(user=owner, sort_by="title", sort_dir="desc")
        assert [t.title for t in result] == ["cherry", "banana", "apple"]

    def test_sort_by_priority_ranks_high_first(self, owner):
        make_task(owner, title="low", priority=Task.Priority.LOW)
        make_task(owner, title="none", priority=Task.Priority.NONE)
        make_task(owner, title="high", priority=Task.Priority.HIGH)
        make_task(owner, title="medium", priority=Task.Priority.MEDIUM)

        result = search_tasks_for_user(user=owner, sort_by="priority")
        assert [t.title for t in result] == ["high", "medium", "low", "none"]

    def test_sort_by_priority_descending_ranks_lowest_first(self, owner):
        make_task(owner, title="low", priority=Task.Priority.LOW)
        make_task(owner, title="none", priority=Task.Priority.NONE)
        make_task(owner, title="high", priority=Task.Priority.HIGH)

        result = search_tasks_for_user(user=owner, sort_by="priority", sort_dir="desc")
        assert [t.title for t in result] == ["none", "low", "high"]

    def test_sort_by_created_at_descending(self, owner):
        make_task(owner, title="first")
        make_task(owner, title="second")

        result = search_tasks_for_user(
            user=owner, sort_by="created_at", sort_dir="desc"
        )
        assert [t.title for t in result] == ["second", "first"]

    def test_invalid_sort_field_is_ignored(self, owner, sample_tasks):
        result = search_tasks_for_user(user=owner, sort_by="bogus_field")
        assert result.count() == len(sample_tasks)


class TestOverdueTasksSelector:
    def make_overdue(self, owner, **overrides):
        data = {
            "title": "Overdue task",
            "owner": owner,
            "due_datetime": timezone.now() - timedelta(days=1),
        }
        data.update(overrides)
        return Task.objects.create(**data)

    def test_returns_incomplete_overdue_tasks(self, owner):
        overdue = self.make_overdue(owner, title="Overdue")
        self.make_overdue(
            owner, title="Completed overdue", status=Task.Status.COMPLETED
        )
        make_task(
            owner, title="Future", due_datetime=timezone.now() + timedelta(days=1)
        )

        result = get_overdue_tasks_for_user(user=owner)
        assert set(result) == {overdue}

    def test_returns_empty_when_nothing_overdue(self, owner):
        make_task(
            owner, title="Future", due_datetime=timezone.now() + timedelta(days=1)
        )
        assert get_overdue_tasks_for_user(user=owner).count() == 0

    def test_overdue_capped_at_limit(self, owner):
        for i in range(OVERDUE_TASKS_LIMIT + 5):
            Task.objects.create(
                owner=owner,
                title=f"Late {i}",
                due_datetime=timezone.now() - timedelta(days=i + 1),
            )

        assert get_overdue_tasks_for_user(user=owner).count() == OVERDUE_TASKS_LIMIT

    def test_is_overdue_property(self, owner):
        overdue = self.make_overdue(owner)
        make_task(
            owner, title="Future", due_datetime=timezone.now() + timedelta(days=1)
        )
        completed = self.make_overdue(owner, status=Task.Status.COMPLETED)
        no_due = make_task(owner, title="No due date")

        assert overdue.is_overdue is True
        assert completed.is_overdue is False
        assert no_due.is_overdue is False


class TestTodayTasksSelector:
    def test_created_today_without_due_date_is_not_in_today(self, owner):
        make_task(owner, title="Created today, no due date")

        result = get_today_tasks_for_user(user=owner)
        assert list(result) == []

    def test_due_today_past_due_time_only_counts_as_overdue(self, owner):
        task = Task.objects.create(
            owner=owner,
            title="Slipped today",
            due_datetime=timezone.now() - timedelta(hours=2),
        )

        assert task not in get_today_tasks_for_user(user=owner)
        assert task in get_overdue_tasks_for_user(user=owner)


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
        assert b'name="sort"' in response.content

    def test_sort_param_orders_results(self, client_logged_in, owner):
        make_task(owner, title="banana")
        make_task(owner, title="apple")

        response = client_logged_in.get(ALL_TASKS_URL, {"sort": "title"})
        assert response.status_code == 200
        assert response.content.index(b"apple") < response.content.index(b"banana")

    def test_invalid_sort_param_is_ignored(self, client_logged_in, owner, sample_tasks):
        response = client_logged_in.get(ALL_TASKS_URL, {"sort": "bogus"})
        assert response.status_code == 200
        assert sample_tasks["grocery"].title.encode() in response.content

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


class TestHomeOverdueSection:
    def make_overdue(self, owner, **overrides):
        data = {
            "title": "Overdue task",
            "owner": owner,
            "due_datetime": timezone.now() - timedelta(days=1),
        }
        data.update(overrides)
        return Task.objects.create(**data)

    def test_overdue_section_shown_with_overdue_tasks(self, client_logged_in, owner):
        self.make_overdue(owner, title="My late task")

        response = client_logged_in.get(HOME_URL)

        assert response.status_code == 200
        assert b">Overdue<" in response.content
        assert b"My late task" in response.content
        assert b"Overdue" in response.content

    def test_overdue_section_hidden_without_overdue_tasks(
        self, client_logged_in, owner
    ):
        make_task(
            owner, title="Future", due_datetime=timezone.now() + timedelta(days=1)
        )

        response = client_logged_in.get(HOME_URL)

        assert b">Overdue<" not in response.content

    def test_overdue_tasks_excluded_from_upcoming(self, owner):
        self.make_overdue(owner, title="Late task")
        future = make_task(
            owner, title="Soon", due_datetime=timezone.now() + timedelta(days=1)
        )

        upcoming = get_upcoming_tasks_for_user(user=owner)
        assert set(upcoming) == {future}
