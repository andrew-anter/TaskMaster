import pytest
from django.core.cache import caches
from django.test import RequestFactory
from django.urls import reverse

from accounts.lockout import (
    LOCKOUT_MAX_FAILURES,
    clear_login_failures,
    is_login_locked,
    record_login_failure,
)
from accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_lockout_cache():
    """Keep lockout counters from leaking between tests."""
    caches["lockout"].clear()


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

    def test_post_password_with_edge_whitespace(self, client):
        """Passwords set via admin/createsuperuser may keep edge whitespace."""
        User.objects.create_user(username="spacer", password="S3cret! ")
        data = {"username": "spacer", "password": "S3cret! "}
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


class TestLockoutCounter:
    def test_counter_uses_lockout_alias_and_clears(self):
        request = RequestFactory().post(reverse("login"), REMOTE_ADDR="198.51.100.1")
        record_login_failure(request=request, username="AliasUser")

        key = "accounts:login_failures:aliasuser:198.51.100.1"
        assert caches["lockout"].get(key) == 1

        clear_login_failures(request=request, username="AliasUser")
        assert caches["lockout"].get(key) is None
        assert not is_login_locked(request=request, username="AliasUser")

    def test_forwarded_for_ignored_unless_trusted(self, settings):
        """Spoofable X-Forwarded-For must not split the counter into new buckets."""
        settings.TRUST_X_FORWARDED_FOR = False
        for attempt in range(LOCKOUT_MAX_FAILURES):
            request = RequestFactory().post(
                reverse("login"),
                HTTP_X_FORWARDED_FOR=f"203.0.113.{attempt}",
                REMOTE_ADDR="10.0.0.1",
            )
            record_login_failure(request=request, username="xffspoof")

        check_request = RequestFactory().post(reverse("login"), REMOTE_ADDR="10.0.0.1")
        assert is_login_locked(request=check_request, username="xffspoof")

    def test_trusted_forwarded_for_is_per_client(self, settings):
        settings.TRUST_X_FORWARDED_FOR = True
        for attempt in range(LOCKOUT_MAX_FAILURES):
            request = RequestFactory().post(
                reverse("login"),
                HTTP_X_FORWARDED_FOR=f"203.0.113.9, 10.0.0.{attempt}",
                REMOTE_ADDR="10.0.0.1",
            )
            record_login_failure(request=request, username="xfffixed")

        locked_request = RequestFactory().post(
            reverse("login"),
            HTTP_X_FORWARDED_FOR="203.0.113.9",
            REMOTE_ADDR="10.0.0.99",
        )
        assert is_login_locked(request=locked_request, username="xfffixed")

        other_client = RequestFactory().post(
            reverse("login"),
            HTTP_X_FORWARDED_FOR="198.51.100.7",
            REMOTE_ADDR="10.0.0.1",
        )
        assert not is_login_locked(request=other_client, username="xfffixed")


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

    def test_invalid_email_rejected_on_email_field(self, client):
        data = {
            "username": "bademail",
            "email": "not-an-email",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("register"), data)
        assert response.status_code == 200
        assert "email" in response.context["form"].errors
        assert not User.objects.filter(username="bademail").exists()

    def test_email_required(self, client):
        data = {
            "username": "noemail",
            "email": "",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("register"), data)
        assert response.status_code == 200
        assert "email" in response.context["form"].errors


class TestLogoutView:
    def test_post_logs_out(self, client):
        user = User.objects.create_user(username="logoutme", password="testpass1234")
        client.force_login(user)
        response = client.post(reverse("logout"), headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert response["HX-Location"] == reverse("login")
        assert "_auth_user_id" not in client.session

    def test_non_htmx_post_redirects_to_login(self, client):
        user = User.objects.create_user(username="nologout", password="testpass1234")
        client.force_login(user)
        response = client.post(reverse("logout"))
        assert response.status_code == 302
        assert response.url == reverse("login")
        assert "_auth_user_id" not in client.session


class TestAllauthSurface:
    def test_allauth_login_redirects_to_canonical_login(self, client):
        response = client.get("/allauth/login/")
        assert response.status_code == 302
        assert response.url == reverse("login")

    def test_allauth_signup_redirects_to_canonical_register(self, client):
        response = client.get("/allauth/signup/")
        assert response.status_code == 302
        assert response.url == reverse("register")


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
