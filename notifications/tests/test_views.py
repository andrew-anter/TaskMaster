import pytest
from django.urls import reverse

from ..selectors import get_unread_notifications_count
from ..services import notify


@pytest.fixture
def client_logged_in(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestNotificationViews:
    def test_badge_requires_authentication(self, client):
        response = client.get(reverse("notification_badge"))
        assert response.status_code in (302, 403)

    def test_badge_renders_unread_count(self, client_logged_in, user):
        notify(recipient=user, type="t", message="x")
        notify(recipient=user, type="t", message="y")

        response = client_logged_in.get(reverse("notification_badge"))

        assert response.status_code == 200
        assert b'id="notification-badge"' in response.content
        assert b">2<" in response.content

    def test_badge_hides_when_no_unread(self, client_logged_in):
        response = client_logged_in.get(reverse("notification_badge"))
        assert response.status_code == 200
        assert b'id="notification-badge"' in response.content

    def test_panel_renders_notifications(self, client_logged_in, user):
        notify(recipient=user, type="t", message="Hello panel")

        response = client_logged_in.get(reverse("notification_panel"))

        assert response.status_code == 200
        assert b"Hello panel" in response.content
        assert b'id="notification-panel-content"' in response.content

    def test_panel_empty_state(self, client_logged_in):
        response = client_logged_in.get(reverse("notification_panel"))
        assert response.status_code == 200
        assert b"No notifications yet" in response.content

    def test_list_page_renders_all(self, client_logged_in, user):
        notify(recipient=user, type="t", message="Hello list")

        response = client_logged_in.get(reverse("notification_list"))

        assert response.status_code == 200
        assert b"Hello list" in response.content
        assert b"Notifications" in response.content

    def test_mark_all_read(self, client_logged_in, user):
        notify(recipient=user, type="t", message="x")
        notify(recipient=user, type="t", message="y")

        response = client_logged_in.post(reverse("notifications_mark_all_read"))

        assert response.status_code == 200
        assert get_unread_notifications_count(user=user) == 0
        assert b'id="notification-badge"' in response.content

    def test_mark_all_read_from_page_returns_list_partial(self, client_logged_in, user):
        notify(recipient=user, type="t", message="x")

        response = client_logged_in.post(
            reverse("notifications_mark_all_read"), {"source": "page"}
        )

        assert response.status_code == 200
        assert b'id="notifications-list"' in response.content
        assert get_unread_notifications_count(user=user) == 0

    def test_mark_read_navigates_to_link(self, client_logged_in, user):
        notification = notify(
            recipient=user,
            type="t",
            message="x",
            link="/tasks/update/1/",
        )
        assert notification is not None

        response = client_logged_in.post(
            reverse("notification_mark_read", args=[notification.pk])
        )

        assert response.status_code == 200
        location = response.headers.get("HX-Location")
        assert location is not None
        assert "/tasks/update/1/" in location
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_read_is_owner_only(self, client, other_user, notification):
        client.force_login(other_user)

        response = client.post(
            reverse("notification_mark_read", args=[notification.pk])
        )

        assert response.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False

    def test_mark_read_ignores_external_links(self, client_logged_in, user):
        external = notify(
            recipient=user,
            type="t",
            message="x",
            link="https://evil.example.com/phish",
        )
        assert external is not None

        response = client_logged_in.post(
            reverse("notification_mark_read", args=[external.pk])
        )

        location = response.headers.get("HX-Location")
        assert location is not None
        assert "evil.example.com" not in location
        assert "/notifications/" in location
