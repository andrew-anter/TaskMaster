import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse

from accounts.lockout import is_login_locked
from accounts.models import User

pytestmark = pytest.mark.django_db


class TestLoginView:
    def test_get_renders_form(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_valid_login(self, client):
        User.objects.create_user(username="testuser", password="testpass1234")
        data = {"username": "testuser", "password": "testpass1234"}
        response = client.post(reverse("login"), data)
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_post_login_with_email(self, client):
        User.objects.create_user(
            username="emailuser",
            email="emailuser@example.com",
            password="testpass1234",
        )
        data = {"username": "emailuser@example.com", "password": "testpass1234"}
        response = client.post(reverse("login"), data)
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_next_safe_relative_redirect(self, client):
        User.objects.create_user(username="nexter", password="testpass1234")
        data = {
            "username": "nexter",
            "password": "testpass1234",
            "next": "/tasks/",
        }
        response = client.post(reverse("login"), data)
        assert response.status_code == 302
        assert response.url == "/tasks/"

    def test_next_external_rejected(self, client):
        User.objects.create_user(username="exter", password="testpass1234")
        data = {
            "username": "exter",
            "password": "testpass1234",
            "next": "https://evil.example.com/",
        }
        response = client.post(reverse("login"), data)
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_lockout_blocks_correct_password(self, client):
        cache.clear()
        User.objects.create_user(username="lockme", password="correct_1234")
        for _ in range(5):
            client.post(
                reverse("login"),
                {"username": "lockme", "password": "wrongpass"},
            )

        response = client.post(
            reverse("login"),
            {"username": "lockme", "password": "correct_1234"},
        )
        assert response.status_code == 429
        assert response.context["form"].non_field_errors()
        assert "_auth_user_id" not in client.session

    def test_lockout_message_replaces_credential_error(self, client):
        """A locked attempt with a wrong password shows only the lockout error."""
        cache.clear()
        User.objects.create_user(username="lockonly", password="correct_1234")
        for _ in range(5):
            client.post(
                reverse("login"),
                {"username": "lockonly", "password": "wrongpass"},
            )

        response = client.post(
            reverse("login"),
            {"username": "lockonly", "password": "wrongpass"},
        )

        assert response.status_code == 429
        errors = response.context["form"].non_field_errors()
        assert len(errors) == 1
        assert "Too many failed sign-in attempts" in str(errors[0])

    def test_successful_login_clears_failures(self, client):
        cache.clear()
        User.objects.create_user(username="clearme", password="correct_1234")
        for _ in range(3):
            client.post(
                reverse("login"),
                {"username": "clearme", "password": "wrongpass"},
            )

        response = client.post(
            reverse("login"),
            {"username": "clearme", "password": "correct_1234"},
        )
        assert response.status_code == 302
        lockout_request = RequestFactory().post(reverse("login"))
        assert not is_login_locked(request=lockout_request, username="clearme")

    def test_post_invalid_credentials(self, client):
        data = {"username": "nouser", "password": "badpass"}
        response = client.post(reverse("login"), data)
        assert response.status_code == 200
        assert response.context["form"].errors

    def test_logged_in_user_redirected(self, client):
        user = User.objects.create_user(username="already", password="logged_in_1234")
        client.force_login(user)
        response = client.get(reverse("login"))
        assert response.status_code == 302


class TestRegisterView:
    def test_get_renders_form(self, client):
        response = client.get(reverse("register"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_creates_user(self, client):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("register"), data)
        assert response.status_code == 302
        assert User.objects.filter(username="newuser").exists()

    def test_post_invalid_data_returns_errors(self, client):
        data = {
            "username": "",
            "email": "not-an-email",
            "password1": "weak",
            "password2": "different",
        }
        response = client.post(reverse("register"), data)
        assert response.status_code == 200
        assert response.context["form"].errors


class TestLogoutView:
    def test_post_logs_out(self, client):
        user = User.objects.create_user(username="logoutme", password="testpass1234")
        client.force_login(user)
        response = client.post(reverse("logout"))
        assert response.status_code == 200
        assert "HX-Location" in response


class TestRootRedirectView:
    def test_authenticated_redirects_to_home(self, client):
        user = User.objects.create_user(username="authed", password="testpass1234")
        client.force_login(user)
        response = client.get(reverse("root_redirect"))
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_anonymous_redirects_to_login(self, client):
        response = client.get(reverse("root_redirect"))
        assert response.status_code == 302
        assert response.url == reverse("login")
