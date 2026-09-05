import pytest
from django.urls import reverse

from accounts.models import User
from labels.models import Label

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_logged_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def sample_label(user):
    return Label.objects.create(name="Work", color="#3B82F6", owner=user)


class TestLabelListView:
    def test_get_renders(self, client_logged_in, sample_label):
        response = client_logged_in.get(reverse("label_list"))
        assert response.status_code == 200
        assert "labels" in response.context
        assert sample_label in response.context["labels"]

    def test_only_shows_own_labels(self, client_logged_in, user):
        other_user = User.objects.create_user(username="other", password="pass1234")
        Label.objects.create(name="Other", color="#000000", owner=other_user)
        Label.objects.create(name="Mine", color="#111111", owner=user)
        response = client_logged_in.get(reverse("label_list"))
        labels = list(response.context["labels"])
        assert len(labels) == 1
        assert labels[0].name == "Mine"


class TestLabelCreateView:
    def test_get_renders_form(self, client_logged_in):
        response = client_logged_in.get(reverse("label_create"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_creates_label(self, client_logged_in, user):
        data = {"name": "New Label", "color": "#EF4444"}
        response = client_logged_in.post(reverse("label_create"), data)
        assert response.status_code in (200, 302)
        assert Label.objects.filter(owner=user, name="New Label").exists()

    def test_post_invalid_color_returns_errors(self, client_logged_in):
        data = {"name": "Bad Color", "color": "#ZZZZZZ"}
        response = client_logged_in.post(reverse("label_create"), data)
        assert response.status_code == 200
        assert response.context["form"].errors

    def test_post_empty_name_returns_errors(self, client_logged_in):
        data = {"name": "", "color": "#EF4444"}
        response = client_logged_in.post(reverse("label_create"), data)
        assert response.status_code == 200
        assert response.context["form"].errors


class TestLabelDetailView:
    def test_get_renders(self, client_logged_in, sample_label):
        response = client_logged_in.get(reverse("label_detail", args=[sample_label.pk]))
        assert response.status_code == 200
        assert response.context["label"] == sample_label

    def test_get_edit_mode(self, client_logged_in, sample_label):
        response = client_logged_in.get(
            reverse("label_detail", args=[sample_label.pk]) + "?mode=edit"
        )
        assert response.status_code == 200
        assert response.context["editing"] is True

    def test_post_updates_label(self, client_logged_in, sample_label):
        data = {"name": "Updated", "color": "#22C55E"}
        response = client_logged_in.post(
            reverse("label_detail", args=[sample_label.pk]), data
        )
        assert response.status_code in (200, 302)
        sample_label.refresh_from_db()
        assert sample_label.name == "Updated"

    def test_other_user_label_returns_404(self, client_logged_in):
        other_user = User.objects.create_user(username="other", password="pass1234")
        label = Label.objects.create(name="Private", color="#000000", owner=other_user)
        response = client_logged_in.get(reverse("label_detail", args=[label.pk]))
        assert response.status_code == 404


class TestLabelUpdateView:
    def test_get_renders_form(self, client_logged_in, sample_label):
        response = client_logged_in.get(reverse("label_update", args=[sample_label.pk]))
        assert response.status_code == 200
        assert "form" in response.context

    def test_post_updates_label(self, client_logged_in, sample_label):
        data = {"name": "Updated Label", "color": "#F59E0B"}
        response = client_logged_in.post(
            reverse("label_update", args=[sample_label.pk]), data
        )
        assert response.status_code in (200, 302)
        sample_label.refresh_from_db()
        assert sample_label.name == "Updated Label"


class TestLabelDeleteView:
    def test_post_deletes_label(self, client_logged_in, sample_label):
        label_id = sample_label.pk
        response = client_logged_in.post(reverse("label_delete", args=[label_id]))
        assert response.status_code in (200, 302)
        assert not Label.objects.filter(pk=label_id).exists()


class TestInlineLabelFormView:
    def test_get_renders(self, client_logged_in):
        response = client_logged_in.get(reverse("inline_label_form"))
        assert response.status_code == 200


class TestInlineLabelCreateView:
    def test_post_creates_label(self, client_logged_in, user):
        data = {"name": "Inline Label", "color": "#8B5CF6"}
        response = client_logged_in.post(reverse("inline_label_create"), data)
        assert response.status_code == 200
        assert Label.objects.filter(owner=user, name="Inline Label").exists()

    def test_post_empty_name_does_not_create(self, client_logged_in, user):
        data = {"name": "", "color": "#8B5CF6"}
        response = client_logged_in.post(reverse("inline_label_create"), data)
        assert response.status_code == 200
        assert not Label.objects.filter(owner=user, name="").exists()
