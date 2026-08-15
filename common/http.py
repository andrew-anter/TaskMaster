from __future__ import annotations

import json

from django.http import HttpResponse


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
