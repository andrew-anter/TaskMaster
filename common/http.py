from __future__ import annotations

import json

from django.http import HttpResponse
from django.urls import reverse

_REFERER_SESSION_KEY = "_http_referrer"


def is_partial_request(request) -> bool:
    """Return True when an HTMX request should receive a partial fragment.

    Browser back/forward restores (``HX-History-Restore-Request``) and boosted
    links swap the entire ``<body>``, so they must receive the full page
    template. Only plain, non-boosted HTMX requests get partial fragments.
    """
    return (
        bool(request.htmx)
        and not request.htmx.boosted
        and not request.htmx.history_restore_request
    )


def hx_location_response(path: str, *, target: str = "#main-content") -> HttpResponse:
    """
    Return an empty HTTP response that instructs HTMX to navigate to ``path``,
    swapping ``target`` into the page.

    Used after mutating actions so the UI reflects the new server state without
    a full page reload.
    """
    response = HttpResponse()
    response["HX-Location"] = json.dumps({"path": path, "target": target})
    return response


def get_referrer_path(request, *, fallback: str | None = None) -> str:
    """Return the path of the previous page stored by ``ReferrerMiddleware``.

    Pops the value from the session so the next navigation starts fresh.
    Falls back to ``fallback`` (defaults to the ``home`` URL).
    """
    if fallback is None:
        fallback = reverse("home")
    return request.session.pop(_REFERER_SESSION_KEY, fallback)
