import json
from unittest.mock import MagicMock

from common.http import hx_location_response, is_partial_request


class TestIsPartialRequest:
    def _make_request(self, htmx=False, boosted=False, history_restore=False):
        request = MagicMock()
        request.htmx = MagicMock()
        request.htmx.__bool__ = lambda self: htmx
        request.htmx.boosted = boosted
        request.htmx.history_restore_request = history_restore
        return request

    def test_non_htmx_request(self):
        request = self._make_request(htmx=False)
        assert is_partial_request(request) is False

    def test_htmx_boosted_request(self):
        request = self._make_request(htmx=True, boosted=True)
        assert is_partial_request(request) is False

    def test_htmx_history_restore_request(self):
        request = self._make_request(htmx=True, history_restore=True)
        assert is_partial_request(request) is False

    def test_plain_htmx_request(self):
        request = self._make_request(htmx=True)
        assert is_partial_request(request) is True

    def test_htmx_boosted_and_history_restore(self):
        request = self._make_request(htmx=True, boosted=True, history_restore=True)
        assert is_partial_request(request) is False


class TestHxLocationResponse:
    def test_default_target(self):
        response = hx_location_response("/tasks/")
        assert response.status_code == 200
        payload = json.loads(response["HX-Location"])
        assert payload == {"path": "/tasks/", "target": "#main-content"}

    def test_custom_target(self):
        response = hx_location_response("/tasks/", target="#custom")
        payload = json.loads(response["HX-Location"])
        assert payload == {"path": "/tasks/", "target": "#custom"}

    def test_empty_path(self):
        response = hx_location_response("")
        payload = json.loads(response["HX-Location"])
        assert payload["path"] == ""
