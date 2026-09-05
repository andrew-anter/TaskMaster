import pytest
from django.urls import reverse

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
